import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import load_google_sheet, calculate_oee
import dash_bootstrap_components as dbc

# --- Register page ---
dash.register_page(__name__, path="/", name="Dashboard")

# --- Konfigurasi Google Sheet ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/13wz2xkVIdJqLdZ9UbUVtFrecnxuMS8Z0QLdoTjF-wLg/edit#gid=0"

# --- Load data awal ---
df_oee = load_google_sheet(SHEET_URL, "oee")
df_downtime = load_google_sheet(SHEET_URL, "downtime")
df, df_harian, df_bulanan, downtime_summary = calculate_oee(df_oee, df_downtime)

# --- Layout ---
layout = dbc.Container([
    html.H2("📊 Dashboard OEE", className="mb-4 mt-2 text-center"),
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(
                id="bulan-dropdown",
                options=[{"label": str(b), "value": str(b)} for b in df_bulanan["bulan"].dropna().astype(str).unique()],
                value=str(df_bulanan["bulan"].max()) if not df_bulanan.empty else None,
                clearable=False,
                style={"width": "100%"}
            )
        ], xs=12, md=6, className="mb-3 mx-auto"),
    ], justify="center"),
    html.Div(id="all-lines-container")
], fluid=True)


# ==============================
# CALLBACKS
# ==============================

@callback(
    Output("all-lines-container", "children"),
    Input("bulan-dropdown", "value")
)
def update_dashboard(selected_month):
    if df.empty:
        return [html.Div("⚠️ Data tidak tersedia")]

    all_lines_layout = []

    # Loop setiap line

    # Filter data OEE dan downtime sesuai bulan yang dipilih
    # Use daily aggregate for KPI and trend chart
    # Filter daily aggregate for selected month
    if df_harian.empty:
        return [html.Div("⚠️ Data tidak tersedia untuk agregat harian")]

    # Add 'bulan' column to df_harian for filtering
    df_harian["bulan"] = df_harian["tanggal"].dt.to_period("M")
    df_harian_bulan = df_harian[df_harian["bulan"].astype(str) == str(selected_month)].copy()
    # For each line in the month (from original df, since df_harian is total per tanggal)
    lines_in_bulan = sorted(df["line"].astype(str).unique())
    for line in lines_in_bulan:
        # Filter original df for this line and month, then aggregate per tanggal
        df_line = df[(df["line"].astype(str) == line) & (df["bulan"].astype(str) == str(selected_month))].copy()
        if df_line.empty:
            continue
        # Aggregate per tanggal for this line
        df_line_harian = df_line.groupby("tanggal").agg({
            "good product output": "sum",
            "hold & all defect": "sum",
            "loading time": "sum",
            "output maksimal": "sum",
            "availability": "mean",  # for info only
            "performance": "mean",
            "quality": "mean",
            "oee": "mean"
        }).reset_index()
        # Calculate daily OEE from totals (not mean)
        with pd.option_context('mode.use_inf_as_na', True):
            denom_perf = df_line_harian["output maksimal"]
            denom_perf = denom_perf.replace(0, pd.NA)
            numer_perf = df_line_harian["good product output"] * df_line_harian["loading time"]
            perf = (numer_perf / denom_perf).replace([float('inf'), -float('inf')], pd.NA)
            perf = (perf - (df_line_harian["hold & all defect"] / 8)) / df_line_harian["loading time"]
            perf = perf.replace([float('inf'), -float('inf')], pd.NA)
            df_line_harian["performance"] = perf * 100

            numer_qual = df_line_harian["good product output"] - df_line_harian["hold & all defect"]
            denom_qual = df_line_harian["good product output"]
            denom_qual = denom_qual.replace(0, pd.NA)
            qual = (numer_qual / denom_qual).replace([float('inf'), -float('inf')], pd.NA)
            df_line_harian["quality"] = qual * 100

            # Downtime per tanggal for this line
            if not df_downtime.empty and "line" in df_downtime.columns:
                df_downtime["tanggal"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce")
                dt_line_harian = df_downtime[(df_downtime["line"].astype(str) == line) & (df_downtime["tanggal"].dt.to_period("M").astype(str) == str(selected_month))]
                downtime_harian = dt_line_harian.groupby("tanggal")["duration"].sum().reset_index()
                df_line_harian = df_line_harian.merge(downtime_harian, on="tanggal", how="left")
                df_line_harian["duration"] = df_line_harian["duration"].fillna(0)
                avail = ((df_line_harian["loading time"] - df_line_harian["duration"]) / df_line_harian["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100
                df_line_harian["availability"] = avail
            else:
                df_line_harian["availability"] = pd.NA

            df_line_harian["oee"] = (df_line_harian["availability"] * df_line_harian["performance"] * df_line_harian["quality"]) / 10000

        # KPI for this line in this month (from daily totals)
        total_loading = df_line_harian["loading time"].sum()
        total_downtime = df_line_harian["duration"].sum() if "duration" in df_line_harian else 0
        total_good = df_line_harian["good product output"].sum()
        total_defect = df_line_harian["hold & all defect"].sum()
        total_output_maks = df_line_harian["output maksimal"].sum()
        # Calculate monthly aggregate KPIs
        with pd.option_context('mode.use_inf_as_na', True):
            availability = ((total_loading - total_downtime) / total_loading) * 100 if total_loading else 0
            performance = (((total_good * total_loading) / total_output_maks - (total_defect / 8)) / total_loading) * 100 if total_loading and total_output_maks else 0
            quality = ((total_good - total_defect) / total_good) * 100 if total_good else 0
            oee = (availability * performance * quality) / 10000

        def kpi_card(title, value, color):
            return html.Div([
                html.H5(title, style={"marginBottom": "10px"}),
                html.H3(f"{value:.1f}%", style={"color": color})
            ], style={
                "flex": "1",
                "backgroundColor": "white",
                "padding": "15px",
                "borderRadius": "8px",
                "textAlign": "center",
                "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"
            })

        def get_color(val):
            if val < 65:
                return "#e74c3c"  # merah
            elif val < 85:
                return "#f1c40f"  # kuning
            else:
                return "#2ecc71"  # hijau

        kpis = dbc.Row([
            dbc.Col(kpi_card("Availability", availability, get_color(availability)), xs=12, md=3, className="mb-2"),
            dbc.Col(kpi_card("Performance", performance, get_color(performance)), xs=12, md=3, className="mb-2"),
            dbc.Col(kpi_card("Quality", quality, get_color(quality)), xs=12, md=3, className="mb-2"),
            dbc.Col(kpi_card("OEE", oee, get_color(oee)), xs=12, md=3, className="mb-2"),
        ], className="mb-3 g-2")

        # --- Chart Tren OEE harian (dari agregat harian per tanggal per line) ---
        df_line_harian = df_line_harian.fillna(0)
        colors = "#3498db"
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_line_harian["tanggal"],
            y=df_line_harian["oee"] / 100,  # agar hover % benar
            mode="lines+markers",
            line=dict(width=3, shape="spline"),
            marker=dict(size=9, color=colors, line=dict(width=2, color="white")),
            customdata=df_line_harian[["availability", "performance", "quality"]] / 100,
            hovertemplate=(
                "<b>Tanggal:</b> %{x|%d-%m-%Y}<br>"
                "<b>OEE:</b> %{y:.1%}<br>"
                "Availability: %{customdata[0]:.1%}<br>"
                "Performance: %{customdata[1]:.1%}<br>"
                "Quality: %{customdata[2]:.1%}<extra></extra>"
            )
        ))
        fig_trend.add_hline(y=0.85, line_dash="dash", line_color="green",
            annotation_text="🎯 Target 85%", annotation_position="top left")
        fig_trend.update_yaxes(tickformat=".0%", title="OEE (%)")
        fig_trend.update_layout(
            title=f"📈 Tren OEE - Line {line} ({selected_month})",
            plot_bgcolor="#f9f9f9",
            paper_bgcolor="#f9f9f9",
            title_font=dict(size=18, color="#2c3e50"),
            font=dict(family="Segoe UI", size=13, color="#2c3e50"),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Segoe UI"),
            margin=dict(l=40, r=20, t=60, b=40)
        )

        # --- Pareto Downtime ---
        # Filter downtime_summary for this line and month
        if "bulan" in downtime_summary.columns:
            dt_line = downtime_summary[(downtime_summary["line"] == line) & (downtime_summary["bulan"].astype(str) == str(selected_month))]
        else:
            dt_line = downtime_summary[downtime_summary["line"] == line]
        if not dt_line.empty:
            fig_pareto = px.bar(
                dt_line,
                x="kategori", y="duration",
                title=f"📊 Pareto Downtime - Line {line}",
                text_auto=True
            )
            fig_pareto.update_yaxes(title="Durasi (menit)")
        else:
            fig_pareto = go.Figure()
            fig_pareto.add_annotation(
                text="⚠️ Tidak ada data downtime",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )

        # Gabungkan section untuk line ini dengan Pareto Downtime
        section = dbc.Card([
            dbc.CardBody([
                html.H3(f"Line {line}", className="mb-3 mt-2 text-center"),
                kpis,
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig_trend, style={"width": "100%", "height": "100%"}), xs=12, md=6, className="mb-3"),
                    dbc.Col(dcc.Graph(figure=fig_pareto, style={"width": "100%", "height": "100%"}), xs=12, md=6, className="mb-3"),
                ], className="g-2")
            ])
        ], className="mb-4 shadow-sm")

        all_lines_layout.append(section)

    return all_lines_layout
