import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table, ctx
import plotly.express as px
import plotly.graph_objects as go

# ====================
# Load Data Functions
# ====================
def load_data():
    file = "oee_data.xlsx"

    # Baca sheet OEE tanpa header dulu
    df_raw = pd.read_excel(file, sheet_name="OEE", header=None)

    # Cari baris header
    header_row = None
    for i, row in df_raw.iterrows():
        row_values = row.astype(str).str.lower().tolist()
        if "availability" in row_values and "performance" in row_values and "quality" in row_values:
            header_row = i
            break

    if header_row is None:
        raise ValueError("❌ Tidak ditemukan header dengan kolom Availability/Performance/Quality")

    # Baca ulang dengan header benar
    df = pd.read_excel(file, sheet_name="OEE", header=header_row, parse_dates=["Tanggal"])
    df = df.rename(columns=lambda x: str(x).strip())

    # Tambah kolom Bulan
    if "Tanggal" in df.columns:
        df["Bulan"] = df["Tanggal"].dt.strftime("%B")

    # Hitung OEE
    df["OEE"] = df["Availability"] * df["Performance"] * df["Quality"]

    return df


def load_losses():
    file = "oee_data.xlsx"
    df = pd.read_excel(file, sheet_name="Losses", parse_dates=["Tanggal"])
    df = df.rename(columns=lambda x: str(x).strip())

    # Tambah kolom Bulan
    if "Tanggal" in df.columns:
        df["Bulan"] = df["Tanggal"].dt.strftime("%B")

    # Ganti NaN jadi "-" supaya tidak muncul di tabel
    df = df.fillna("-")

    return df


# ====================
# Load awal
# ====================
df = load_data()
df_losses = load_losses()

# Urutan line dinamis
line_order = sorted(df["Line"].astype(str).unique())

# Bulan terbaru by tanggal
latest_month = df["Tanggal"].max().strftime("%B")

# ====================
# Inisialisasi App
# ====================
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Dashboard OEE & Losses"


# Fungsi buat KPI card
def kpi_card(title, value, color):
    return html.Div([
        html.H4(title, style={"marginBottom": "10px", "color": "#2c3e50"}),
        html.H2(f"{value:.1f}%", style={"color": color, "margin": "0"})
    ], style={
        "flex": "1",
        "backgroundColor": "white",
        "padding": "20px",
        "borderRadius": "12px",
        "boxShadow": "0 2px 6px rgba(0,0,0,0.1)",
        "textAlign": "center"
    })


# Fungsi untuk menentukan warna sesuai nilai
def get_color(value):
    if value < 65:
        return "#e74c3c"   # merah
    elif value < 85:
        return "#f1c40f"   # kuning
    else:
        return "#2ecc71"   # hijau


# ====================
# Layout
# ====================
app.layout = html.Div([
    html.H1("📊 Dashboard OEE PT. Calf Indonesia", style={
        "textAlign": "center",
        "color": "#2c3e50",
        "marginBottom": "20px"
    }),

    # Filter Bulan
    html.Div([
        html.Label("Pilih Bulan:"),
        dcc.Dropdown(
            id="bulan-filter",
            options=[{"label": str(b), "value": str(b)}
                     for b in df["Bulan"].dropna().astype(str).unique()],
            value=latest_month,  # default bulan terbaru
            clearable=False
        ),
    ], style={"width": "40%", "margin": "20px auto"}),

    # Container semua line
    html.Div(id="all-lines-container")
], style={"backgroundColor": "#f9f9f9", "padding": "20px", "fontFamily": "Segoe UI"})


# ====================
# Callback Update Semua Line
# ====================
@app.callback(
    Output("all-lines-container", "children"),
    Input("bulan-filter", "value")
)
def update_all_lines(bulan):
    df = load_data()
    df_losses = load_losses()

    all_lines_layout = []

    for line in line_order:
        df_line = df[(df["Bulan"].astype(str) == str(bulan)) &
                     (df["Line"].astype(str) == str(line))]

        if df_line.empty:
            continue

        # Hitung KPI
        availability = df_line["Availability"].mean() * 100
        performance = df_line["Performance"].mean() * 100
        quality = df_line["Quality"].mean() * 100
        oee = df_line["OEE"].mean() * 100

        # KPI cards
        kpi_cards = html.Div([
            kpi_card("Availability", availability, get_color(availability)),
            kpi_card("Performance", performance, get_color(performance)),
            kpi_card("Quality", quality, get_color(quality)),
            kpi_card("OEE", oee, get_color(oee))
        ], style={"display": "flex", "gap": "15px", "marginBottom": "15px"})

        # Tren OEE line tertentu
        fig_trend = px.line(
            df_line, x="Tanggal", y="OEE",
            title=f"📈 Tren OEE - Line {line} ({bulan})", markers=True
        )
        fig_trend.update_traces(
            marker=dict(size=8, color="#3498db"),
            selected=dict(marker=dict(size=12, color="red")),
            unselected=dict(marker=dict(opacity=0.5))
        )
        fig_trend.update_yaxes(tickformat=".0%")
        fig_trend.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            clickmode="event+select"
        )

        # Pareto losses line tertentu
        df_loss_line = df_losses[(df_losses["Bulan"].astype(str) == str(bulan)) &
                                 (df_losses["Line"].astype(str) == str(line))]
        fig_pareto = go.Figure()
        if not df_loss_line.empty:
            pareto = df_loss_line.groupby("Sub Kategori")["Loss Time"].sum().reset_index()
            pareto = pareto.sort_values("Loss Time", ascending=False)
            pareto["Cumulative %"] = pareto["Loss Time"].cumsum() / pareto["Loss Time"].sum() * 100

            fig_pareto.add_trace(go.Bar(
                x=pareto["Sub Kategori"], y=pareto["Loss Time"],
                name="Loss Time",
                marker=dict(color="#3498db"),
                selected=dict(marker=dict(color="red")),
                unselected=dict(marker=dict(opacity=0.5))
            ))
            fig_pareto.add_trace(go.Scatter(
                x=pareto["Sub Kategori"], y=pareto["Cumulative %"],
                name="Cumulative %", yaxis="y2", mode="lines+markers"
            ))
            fig_pareto.update_layout(
                title="Pareto Losses",
                yaxis=dict(title="Loss Time"),
                yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 110]),
                plot_bgcolor="white", paper_bgcolor="white",
                clickmode="event+select"
            )

        # Detail Losses tabel (collapsible + reset button)
        losses_table = dash_table.DataTable(
            id=f"losses-table-{line}",
            columns=[{"name": c, "id": c} for c in df_loss_line.columns],
            data=df_loss_line.astype(str).to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto", "maxHeight": "300px", "overflowY": "scroll"},
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
            style_header={
                "backgroundColor": "#2c3e50",
                "color": "white",
                "fontWeight": "bold"
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f2f2f2"}
            ]
        )

        reset_button = html.Button(
            "Reset Filter",
            id=f"reset-{line}",
            n_clicks=0,
            style={"margin": "10px 0", "padding": "6px 12px", "borderRadius": "6px",
                   "border": "none", "backgroundColor": "#3498db", "color": "white",
                   "cursor": "pointer"}
        )

        losses_section = html.Details([
            html.Summary("📋 Detail Losses", style={"cursor": "pointer", "fontWeight": "bold"}),
            reset_button,
            losses_table
        ], open=False)

        # Gabungkan section per line
        section = html.Div([
            html.H2(f"Line {line}", style={"color": "#2c3e50"}),
            kpi_cards,
            html.Div([
                dcc.Graph(id=f"trend-oee-{line}", figure=fig_trend,
                          style={"flex": "1", "marginRight": "10px"}),
                dcc.Graph(id=f"pareto-{line}", figure=fig_pareto, style={"flex": "1"})
            ], style={"display": "flex", "marginBottom": "20px"}),
            losses_section
        ], style={"marginBottom": "50px", "padding": "20px", "backgroundColor": "#fdfdfd",
                  "borderRadius": "12px", "boxShadow": "0 2px 6px rgba(0,0,0,0.1)"})

        all_lines_layout.append(section)

    return all_lines_layout


# ====================
# Callback Update Losses per Line
# ====================
def register_losses_callback(line):
    @app.callback(
        Output(f"losses-table-{line}", "data"),
        [Input(f"trend-oee-{line}", "clickData"),
         Input(f"pareto-{line}", "clickData"),
         Input(f"reset-{line}", "n_clicks")],
        State("bulan-filter", "value")
    )
    def update_losses(trend_click, pareto_click, reset_clicks, bulan):
        df_losses = load_losses()
        df_line = df_losses[(df_losses["Bulan"].astype(str) == str(bulan)) &
                            (df_losses["Line"].astype(str) == str(line))]

        trigger_id = ctx.triggered_id

        if trigger_id == f"trend-oee-{line}" and trend_click:
            tanggal = pd.to_datetime(trend_click["points"][0]["x"]).normalize()
            df_line["Tanggal"] = pd.to_datetime(df_line["Tanggal"], errors="coerce").dt.normalize()
            df_line = df_line[df_line["Tanggal"] == tanggal]

        elif trigger_id == f"pareto-{line}" and pareto_click:
            kategori = pareto_click["points"][0]["x"]
            df_line = df_line[df_line["Sub Kategori"] == kategori]

        # Ganti NaN jadi "-" sebelum ditampilkan
        return df_line.fillna("-").astype(str).to_dict("records")


# Daftarkan callback untuk setiap line yang ada
for line in line_order:
    register_losses_callback(line)


# ====================
# Run App
# ====================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
