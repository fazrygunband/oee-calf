import dash
from dash import dcc, html, Input, Output, callback, State, ALL
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
                id="tahun-dropdown",
                options=[{"label": str(y), "value": str(y)} for y in sorted(df["tanggal"].dt.year.dropna().astype(int).unique())],
                value=str(df["tanggal"].dt.year.max()) if "tanggal" in df.columns and not df.empty else None,
                clearable=False,
                placeholder="Pilih Tahun"
            )
        ], xs=12, md=3, className="mb-3"),
        dbc.Col([
            dcc.Dropdown(
                id="bulan-dropdown",
                # options akan diupdate oleh callback berdasarkan tahun yang dipilih
                options=[{"label": pd.to_datetime(str(b) + "-01").strftime("%B %Y"), "value": str(b)} for b in df_bulanan["bulan"].dropna().astype(str).unique()],
                value=str(df_bulanan["bulan"].max()) if not df_bulanan.empty else None,
                clearable=False,
                style={"width": "100%"}
            )
        ], xs=12, md=6, className="mb-3 mx-auto"),
    ], justify="center"),
    html.Div(id="all-lines-container")
    ,
    # Modal untuk menampilkan detail saat klik pada grafik
    dbc.Modal([
        dbc.ModalHeader("Detail"),
        dbc.ModalBody(id="detail-modal-body"),
        dbc.ModalFooter(dbc.Button("Close", id="close-detail", n_clicks=0))
    ], id="detail-modal", is_open=False, size="lg")
], fluid=True)


# ==============================
# CALLBACKS
# ==============================

@callback(
    Output("all-lines-container", "children"),
    Input("bulan-dropdown", "value"),
    Input("tahun-dropdown", "value")
)
def update_dashboard(selected_month, selected_year):
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
    # Support 'ALL' month: if selected_month == 'ALL', show all months in selected_year (if provided)
    if selected_month and str(selected_month) != 'ALL':
        df_harian_bulan = df_harian[df_harian["bulan"].astype(str) == str(selected_month)].copy()
        title_period_label = pd.to_datetime(str(selected_month) + "-01").strftime("%B %Y") if pd.notna(pd.to_datetime(str(selected_month) + "-01", errors='coerce')) else str(selected_month)
    elif selected_year:
        df_harian_bulan = df_harian[df_harian["bulan"].astype(str).str.startswith(str(selected_year))].copy()
        title_period_label = str(selected_year)
    else:
        df_harian_bulan = df_harian.copy()
        title_period_label = "All Months"

    # For each line use lines present in the filtered df_harian_bulan
    lines_in_bulan = sorted(df_harian_bulan["line"].astype(str).unique())
    for line in lines_in_bulan:
        # Filter original df for this line and selected month/year, then aggregate per tanggal
        mask = (df["line"].astype(str) == line)
        if selected_month and str(selected_month) != 'ALL':
            mask = mask & (df["bulan"].astype(str) == str(selected_month))
        elif selected_year:
            mask = mask & (df["bulan"].astype(str).str.startswith(str(selected_year)))
        # else keep all months
        df_line = df[mask].copy()
        if df_line.empty:
            continue
        # Aggregate per tanggal for this line (daily) OR per month if 'ALL' selected
        if selected_month and str(selected_month) == 'ALL':
            # aggregate per bulan
            # ensure df_line has 'bulan' as Period
            df_line["bulan"] = pd.to_datetime(df_line["tanggal"]).dt.to_period("M")
            agg = df_line.groupby("bulan").agg({
                "good product output": "sum",
                "hold & all defect": "sum",
                "loading time": "sum",
                "output maksimal": "sum"
            }).reset_index()
            # convert 'bulan' Period to a datetime for plotting (use first day of month)
            agg["tanggal"] = agg["bulan"].dt.to_timestamp()
            # initialize placeholders for calculated metrics
            agg["availability"] = pd.NA
            agg["performance"] = pd.NA
            agg["quality"] = pd.NA
            agg["oee"] = pd.NA
            df_line_harian = agg[["tanggal", "bulan", "good product output", "hold & all defect", "loading time", "output maksimal", "availability", "performance", "quality", "oee"]]
        else:
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

            # Downtime per tanggal or per bulan for this line
            if not df_downtime.empty and "line" in df_downtime.columns:
                df_downtime["tanggal"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce")
                if selected_month and str(selected_month) == 'ALL':
                    # aggregate downtime per bulan
                    dt_line_harian = df_downtime[(df_downtime["line"].astype(str) == line) & (df_downtime["tanggal"].dt.to_period("M").astype(str).str.startswith(str(selected_year)) if selected_year else True)]
                    downtime_harian = dt_line_harian.groupby(dt_line_harian["tanggal"].dt.to_period("M")).agg({"duration": "sum"}).reset_index()
                    # convert period index to timestamp aligned with agg 'bulan'
                    downtime_harian.columns = ["bulan","duration"]
                    downtime_harian["tanggal"] = downtime_harian["bulan"].dt.to_timestamp()
                    df_line_harian = df_line_harian.merge(downtime_harian[["tanggal","duration"]], on="tanggal", how="left")
                    df_line_harian["duration"] = df_line_harian["duration"].fillna(0)
                    avail = ((df_line_harian["loading time"] - df_line_harian["duration"]) / df_line_harian["loading time"]).replace([float('inf'), -float('inf')], pd.NA) * 100
                    df_line_harian["availability"] = avail
                else:
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
        # pilih hovertemplate berbeda untuk mode bulanan vs harian
        if selected_month and str(selected_month) == 'ALL':
            hover_tmpl = (
                "<b>Bulan:</b> %{x|%B %Y}<br>"
                "<b>OEE:</b> %{y:.1%}<br>"
                "Availability: %{customdata[0]:.1%}<br>"
                "Performance: %{customdata[1]:.1%}<br>"
                "Quality: %{customdata[2]:.1%}<extra></extra>"
            )
            xaxis_config = dict(tickformat="%b %Y")
        else:
            hover_tmpl = (
                "<b>Tanggal:</b> %{x|%d-%m-%Y}<br>"
                "<b>OEE:</b> %{y:.1%}<br>"
                "Availability: %{customdata[0]:.1%}<br>"
                "Performance: %{customdata[1]:.1%}<br>"
                "Quality: %{customdata[2]:.1%}<extra></extra>"
            )
            xaxis_config = dict()

        fig_trend.add_trace(go.Scatter(
            x=df_line_harian["tanggal"],
            y=df_line_harian["oee"] / 100,  # agar hover % benar
            mode="lines+markers",
            line=dict(width=3, shape="spline"),
            marker=dict(size=9, color=colors, line=dict(width=2, color="white")),
            customdata=df_line_harian[["availability", "performance", "quality"]] / 100,
            hovertemplate=hover_tmpl
        ))
        fig_trend.add_hline(y=0.85, line_dash="dash", line_color="green",
            annotation_text="🎯 Target 85%", annotation_position="top left")
        fig_trend.update_yaxes(tickformat=".0%", title="OEE (%)")
        fig_trend.update_layout(
            title=f"📈 Tren OEE - Line {line} ({title_period_label})",
            plot_bgcolor="#f9f9f9",
            paper_bgcolor="#f9f9f9",
            title_font=dict(size=18, color="#2c3e50"),
            font=dict(family="Segoe UI", size=13, color="#2c3e50"),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)", **xaxis_config),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Segoe UI"),
            margin=dict(l=40, r=20, t=60, b=40)
        )

        # --- Pareto Downtime ---
        # Filter downtime_summary for this line and month
        if "bulan" in downtime_summary.columns:
            if selected_month and str(selected_month) != 'ALL':
                dt_line = downtime_summary[(downtime_summary["line"] == line) & (downtime_summary["bulan"].astype(str) == str(selected_month))]
            elif selected_year:
                if selected_month and str(selected_month) == 'ALL':
                    tmp = downtime_summary[(downtime_summary["line"] == line) & (downtime_summary["bulan"].astype(str).str.startswith(str(selected_year)))].copy()
                    if not tmp.empty:
                        dt_line = tmp.groupby("kategori")["duration"].sum().reset_index()
                    else:
                        dt_line = tmp
                else:
                    dt_line = downtime_summary[(downtime_summary["line"] == line) & (downtime_summary["bulan"].astype(str).str.startswith(str(selected_year)))]
            else:
                dt_line = downtime_summary[downtime_summary["line"] == line]
        else:
            dt_line = downtime_summary[downtime_summary["line"] == line]
        if not dt_line.empty:
            # normalize dataframe: ensure it has kategori & duration
            try:
                df_p = dt_line[["kategori", "duration"]].copy()
            except Exception:
                # fallback: try to rename columns if aggregated differently
                df_p = dt_line.reset_index()
                if "duration" not in df_p.columns and df_p.shape[1] >= 2:
                    # assume second column is duration
                    df_p = df_p.rename(columns={df_p.columns[1]: "duration", df_p.columns[0]: "kategori"})[["kategori","duration"]]

            # drop NA and ensure numeric
            df_p = df_p.dropna(subset=["duration"]).copy()
            df_p["duration"] = pd.to_numeric(df_p["duration"], errors="coerce").fillna(0)
            total = df_p["duration"].sum()
            # sort descending
            df_p = df_p.sort_values("duration", ascending=False)
            # percentage share
            df_p["pct"] = (df_p["duration"] / total).fillna(0)

            # build bar with percent labels above bars
            fig_pareto = px.bar(
                df_p,
                x="kategori", y="duration",
                title=f"📊 Pareto Downtime - Line {line}",
                text=df_p["pct"].apply(lambda v: f"{v:.1%}")
            )
            fig_pareto.update_traces(textposition="outside")
            fig_pareto.update_yaxes(title="Durasi (menit)")
            # ensure bars are ordered by duration descending
            fig_pareto.update_layout(xaxis={'categoryorder':'array','categoryarray':df_p['kategori'].tolist()})
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
                    # Tambah id pattern-matching agar kita bisa menangani klik per-line
                    dbc.Col(dcc.Graph(id={"type": "oee-trend", "line": str(line)}, figure=fig_trend, style={"width": "100%", "height": "100%"}), xs=12, md=6, className="mb-3"),
                    dbc.Col(dcc.Graph(id={"type": "pareto", "line": str(line)}, figure=fig_pareto, style={"width": "100%", "height": "100%"}), xs=12, md=6, className="mb-3"),
                ], className="g-2")
            ])
        ], className="mb-4 shadow-sm")

        all_lines_layout.append(section)

    return all_lines_layout


# Callback untuk mengisi opsi bulan berdasarkan tahun yang dipilih
@callback(
    Output("bulan-dropdown", "options"),
    Output("bulan-dropdown", "value"),
    Input("tahun-dropdown", "value")
)
def update_bulan_options(selected_year):
    if df_bulanan.empty:
        return [], None
    try:
        # df_bulanan['bulan'] adalah Period[M], konversi ke string 'YYYY-MM'
        bulan_all = df_bulanan["bulan"].astype(str)
        if selected_year:
            opts = sorted([b for b in bulan_all.unique() if b.startswith(str(selected_year))])
        else:
            opts = sorted(list(bulan_all.unique()))

        # Buat label seperti 'September 2025' namun value tetap 'YYYY-MM'
        options = []
        # tambahkan opsi All Month pada awal list
        options.append({"label": "All Month", "value": "ALL"})
        for b in opts:
            try:
                label = pd.to_datetime(str(b) + "-01").strftime("%B %Y")
            except Exception:
                label = str(b)
            options.append({"label": label, "value": str(b)})

        # default value: jika ada opsi selain ALL pilih yang terakhir (paling baru), else 'ALL'
        value = options[-1]["value"] if len(options) > 1 else "ALL"
        return options, value
    except Exception:
        return [], None


# Callback untuk menangani klik pada grafik (OEE trend & Pareto)
@callback(
    Output("detail-modal", "is_open"),
    Output("detail-modal-body", "children"),
    Input({"type": "oee-trend", "line": ALL}, "clickData"),
    Input({"type": "pareto", "line": ALL}, "clickData"),
    Input("close-detail", "n_clicks"),
    State("detail-modal", "is_open"),
    State("bulan-dropdown", "value"),
    State("tahun-dropdown", "value"),
    prevent_initial_call=True
)
def handle_graph_click(oee_clicks, pareto_clicks, close_clicks, is_open, selected_month, selected_year):
    """Menangani klik pada grafik. Jika klik pada tren OEE -> tampilkan detail tanggal & downtime hari itu.
    Jika klik pada pareto -> tampilkan daftar downtime untuk kategori yang diklik.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, dash.no_update
    trig = ctx.triggered[0]
    prop = trig["prop_id"].split(".")[0]
    try:
        triggered = eval(prop)
    except Exception:
        # bisa jadi tombol close
        if trig["prop_id"].startswith("close-detail"):
            return False, ""
        return is_open, dash.no_update

    data = None
    # cari clickData yang sesuai index pada inputs
    if triggered.get("type") == "oee-trend":
        # oee_clicks adalah list paralel sesuai semua grafik oee-trend
        # temukan index yang memiliki clickData
        for cd in oee_clicks:
            if cd:
                data = cd
                break
        if not data:
            return is_open, dash.no_update
        # ambil info tanggal, y, customdata
        point = data.get("points", [])[0]
        tanggal = point.get("x")
        oee_val = point.get("y")
        custom = point.get("customdata") or []
        availability = custom[0] if len(custom) > 0 else None
        performance = custom[1] if len(custom) > 1 else None
        quality = custom[2] if len(custom) > 2 else None
        line = triggered.get("line")
        # buat isi modal: ringkasan dan daftar downtime (jika ada)
        # format tanggal header sebagai YYYY-MM-DD
        try:
            header_date = pd.to_datetime(tanggal, errors="coerce").strftime("%Y-%m-%d") if pd.notna(pd.to_datetime(tanggal, errors="coerce")) else str(tanggal)
        except Exception:
            header_date = str(tanggal)

        # Prepare a body with KPI cards (computed from raw data) plus clicked OEE
        # Compute daily totals from original df and df_downtime for the clicked date
        try:
            sel_date_dt = pd.to_datetime(tanggal, errors="coerce")
        except Exception:
            sel_date_dt = None

        total_loading = total_downtime = total_good = total_defect = total_output_maks = None
        if sel_date_dt is not None and pd.notna(sel_date_dt):
            sel_date_only = sel_date_dt.date()
            # ensure df tanggal parsed
            try:
                df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
            except Exception:
                pass
            df_day_line = df[(df["line"].astype(str) == str(line)) & (df["tanggal"].dt.date == sel_date_only)]
            if not df_day_line.empty:
                total_loading = df_day_line["loading time"].sum() if "loading time" in df_day_line.columns else 0
                total_good = df_day_line["good product output"].sum() if "good product output" in df_day_line.columns else 0
                total_defect = df_day_line["hold & all defect"].sum() if "hold & all defect" in df_day_line.columns else 0
                total_output_maks = df_day_line["output maksimal"].sum() if "output maksimal" in df_day_line.columns else 0
            # downtime
            try:
                df_downtime["tanggal"] = pd.to_datetime(df_downtime["tanggal"], errors="coerce")
            except Exception:
                pass
            dt_sel = df_downtime[(df_downtime["line"].astype(str) == str(line)) & (df_downtime["tanggal"].dt.date == sel_date_only)]
            if not dt_sel.empty and "duration" in dt_sel.columns:
                total_downtime = dt_sel["duration"].sum()
            else:
                total_downtime = 0

        # compute KPIs
        def safe_div(a, b):
            try:
                return a / b
            except Exception:
                return None

        availability_val = None
        performance_val = None
        quality_val = None
        oee_val_calc = None
        if total_loading and total_loading > 0:
            if total_downtime is None:
                total_downtime = 0
            availability_val = ((total_loading - total_downtime) / total_loading) * 100
        if total_output_maks and total_loading and total_loading > 0:
            try:
                performance_val = (((total_good * total_loading) / total_output_maks - (total_defect / 8)) / total_loading) * 100
            except Exception:
                performance_val = None
        if total_good and total_good > 0:
            quality_val = ((total_good - total_defect) / total_good) * 100
        if availability_val is not None and performance_val is not None and quality_val is not None:
            oee_val_calc = (availability_val * performance_val * quality_val) / 10000

        # small helper for color
        def get_color_local(val):
            try:
                if val is None:
                    return "#7f8c8d"
                if val < 65:
                    return "#e74c3c"
                elif val < 85:
                    return "#f1c40f"
                else:
                    return "#2ecc71"
            except Exception:
                return "#7f8c8d"

        kpi_cards = html.Div([
            html.Div([
                html.H6("Availability", style={"marginBottom": "6px"}),
                html.H4(f"{availability_val:.1f}%" if availability_val is not None else "-", style={"color": get_color_local(availability_val)})
            ], style={"flex": "1", "backgroundColor": "white", "padding": "10px", "borderRadius": "6px", "textAlign": "center", "marginRight": "6px"}),
            html.Div([
                html.H6("Performance", style={"marginBottom": "6px"}),
                html.H4(f"{performance_val:.1f}%" if performance_val is not None else "-", style={"color": get_color_local(performance_val)})
            ], style={"flex": "1", "backgroundColor": "white", "padding": "10px", "borderRadius": "6px", "textAlign": "center", "marginRight": "6px"}),
            html.Div([
                html.H6("Quality", style={"marginBottom": "6px"}),
                html.H4(f"{quality_val:.1f}%" if quality_val is not None else "-", style={"color": get_color_local(quality_val)})
            ], style={"flex": "1", "backgroundColor": "white", "padding": "10px", "borderRadius": "6px", "textAlign": "center", "marginRight": "6px"}),
            html.Div([
                html.H6("OEE", style={"marginBottom": "6px"}),
                html.H4(f"{oee_val_calc:.1f}%" if oee_val_calc is not None else (f"{oee_val:.1%}" if isinstance(oee_val, (int, float)) else "-"), style={"color": get_color_local(oee_val_calc if oee_val_calc is not None else (oee_val*100 if isinstance(oee_val,(int,float)) else None))})
            ], style={"flex": "1", "backgroundColor": "white", "padding": "10px", "borderRadius": "6px", "textAlign": "center"}),
        ], style={"display": "flex", "gap": "6px", "marginTop": "10px", "marginBottom": "10px"})

        # raw numbers summary
        summary = html.Div([
            html.P(f"Loading time: {total_loading}"),
            html.P(f"Downtime: {total_downtime}"),
            html.P(f"Good output: {total_good}"),
            html.P(f"Defect: {total_defect}"),
            html.P(f"Output maksimal: {total_output_maks}"),
        ], style={"fontSize": "13px", "color": "#2c3e50"})

        body = [html.H5(f"Line {line} - {header_date}"), kpi_cards, summary]
        # tambahkan table downtime jika ada
        try:
            # filter df_downtime global
            dt = df_downtime.copy()
            dt["tanggal"] = pd.to_datetime(dt["tanggal"], errors="coerce")
            # jika ada bulan yang dipilih pada dashboard, filter downtime ke bulan itu saja
            if selected_month and str(selected_month) != 'ALL':
                try:
                    dt = dt[dt["tanggal"].dt.to_period("M").astype(str) == str(selected_month)]
                except Exception:
                    pass
            elif selected_year:
                try:
                    dt = dt[dt["tanggal"].dt.to_period("M").astype(str).str.startswith(str(selected_year))]
                except Exception:
                    pass

            # Bandingkan berdasarkan date-only untuk mengabaikan komponen waktu
            sel_date = pd.to_datetime(tanggal, errors="coerce")
            if pd.notna(sel_date):
                sel_date = sel_date.date()
                df_sel = dt[(dt["line"].astype(str) == str(line)) & (dt["tanggal"].dt.date == sel_date)]
            else:
                df_sel = pd.DataFrame()

            if not df_sel.empty:
                # Header termasuk tanggal, start, finish (diformat HH:MM:SS), dan kolom lain
                rows = [html.Tr([html.Th(col) for col in ["tanggal","start","finish","kategori","duration","workcenter","proses","equipment"]])]
                for _, r in df_sel.iterrows():
                    # format tanggal sebagai YYYY-MM-DD
                    t_val = r.get("tanggal")
                    try:
                        t_str = pd.to_datetime(t_val, errors="coerce").strftime("%Y-%m-%d") if pd.notna(pd.to_datetime(t_val, errors="coerce")) else str(t_val)
                    except Exception:
                        t_str = str(t_val)

                    # fungsi bantu untuk format waktu ke HH:MM:SS bila memungkinkan
                    def fmt_time(val):
                        if val is None or val == "":
                            return ""
                        parsed = pd.to_datetime(val, errors="coerce")
                        if pd.notna(parsed):
                            return parsed.strftime("%H:%M:%S")
                        # jika bukan parseable, kembalikan string apa adanya
                        return str(val)

                    start = fmt_time(r.get("start"))
                    finish = fmt_time(r.get("finish"))
                    rows.append(html.Tr([html.Td(x) for x in [t_str, start, finish, r.get("kategori", ''), r.get("duration", ''), r.get("workcenter", ''), r.get("proses", ''), r.get("equipment", '')]]))

                body.append(html.H6("Downtime pada hari ini:"))
                body.append(html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"}))
        except Exception:
            pass

        return True, body

    if triggered.get("type") == "pareto":
        for cd in pareto_clicks:
            if cd:
                data = cd
                break
        if not data:
            return is_open, dash.no_update
        point = data.get("points", [])[0]
        kategori = point.get("x")
        line = triggered.get("line")
        # tampilkan list downtime untuk kategori ini pada line dan bulan yang relevan
        body = [html.H5(f"Line {line} - Kategori: {kategori}" )]
        try:
            dt = df_downtime.copy()
            dt["tanggal"] = pd.to_datetime(dt["tanggal"], errors="coerce")
            # jika ada bulan yang dipilih pada dashboard, filter downtime ke bulan itu saja
            if selected_month and str(selected_month) != 'ALL':
                try:
                    dt = dt[dt["tanggal"].dt.to_period("M").astype(str) == str(selected_month)]
                except Exception:
                    pass
            elif selected_year:
                try:
                    dt = dt[dt["tanggal"].dt.to_period("M").astype(str).str.startswith(str(selected_year))]
                except Exception:
                    pass
            # bulan deduksi: jika point memiliki customdata atau kita gunakan semua bulan
            df_sel = dt[(dt["line"].astype(str) == str(line)) & (dt["kategori"] == kategori)]
            if not df_sel.empty:
                rows = [html.Tr([html.Th(col) for col in ["tanggal","start","finish","duration","workcenter","proses","equipment"]])]

                def fmt_time(val):
                    if val is None or val == "":
                        return ""
                    parsed = pd.to_datetime(val, errors="coerce")
                    if pd.notna(parsed):
                        return parsed.strftime("%H:%M:%S")
                    return str(val)

                for _, r in df_sel.sort_values("tanggal", ascending=False).iterrows():
                    # format tanggal sebagai YYYY-MM-DD
                    t_val = r.get("tanggal")
                    try:
                        t_str = pd.to_datetime(t_val, errors="coerce").strftime("%Y-%m-%d") if pd.notna(pd.to_datetime(t_val, errors="coerce")) else str(t_val)
                    except Exception:
                        t_str = str(t_val)

                    start = fmt_time(r.get("start"))
                    finish = fmt_time(r.get("finish"))
                    rows.append(html.Tr([html.Td(x) for x in [t_str, start, finish, r.get("duration", ''), r.get("workcenter", ''), r.get("proses", ''), r.get("equipment", '')]]))
                body.append(html.Table(rows, style={"width": "100%", "borderCollapse": "collapse"}))
            else:
                body.append(html.P("Tidak ada downtime untuk kategori ini."))
        except Exception:
            body.append(html.P("Gagal mengambil data downtime."))
        return True, body

    # fallback: jika tombol close diklik
    if trig["prop_id"].startswith("close-detail"):
        return False, ""
    return is_open, dash.no_update
