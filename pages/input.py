import dash
from dash import html, dcc, Input, Output, State
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import dash_bootstrap_components as dbc
import uuid
from dash.dependencies import ALL

dash.register_page(__name__, path="/input", name="Input Data")

layout = dbc.Container([
    dcc.Store(id="user-session", storage_type="session"),
    dcc.Store(id="downtime-store"),
    html.Div(id="input-content")
], fluid=True)

# --- Callback simpan ke Google Sheet ---
def write_to_gsheet_oee(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/13wz2xkVIdJqLdZ9UbUVtFrecnxuMS8Z0QLdoTjF-wLg/edit#gid=0").worksheet("oee")
    sheet.append_row(data)

def write_to_gsheet_downtime(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/13wz2xkVIdJqLdZ9UbUVtFrecnxuMS8Z0QLdoTjF-wLg/edit#gid=0").worksheet("downtime")
    sheet.append_row(data)

from dash import callback, Output, Input, State, html

@callback(
    Output("input-content", "children"),
    Input("user-session", "data")
)
def render_input_content(user_data):
    if not user_data or not user_data.get("user"):
        return dbc.Alert("Silakan login terlebih dahulu untuk menginput data.", color="warning", className="mt-4 text-center")
    return dbc.Card([
        dbc.CardBody([
            html.H2("📝 Input Data OEE & Downtime", className="mb-4 mt-2 text-center"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tanggal"),
                    dbc.Input(id="tanggal-input", type="text", placeholder="YYYY-MM-DD", className="mb-2"),
                ], md=4),
                dbc.Col([
                    dbc.Label("Line"),
                    dbc.Input(id="line-input", type="text", placeholder="Line 1", className="mb-2"),
                ], md=4),
                dbc.Col([
                    dbc.Label("Shift"),
                    dbc.Input(id="shift-input", type="text", placeholder="1/2/3", className="mb-2"),
                ], md=4),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("SKU/Produk"),
                    dbc.Input(id="sku-input", type="text", placeholder="Nama Produk", className="mb-2"),
                ], md=6),
                dbc.Col([
                    dbc.Label("Loading Time (menit)"),
                    dbc.Input(id="loading-time-input", type="number", placeholder="480", className="mb-2"),
                ], md=6),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Output Maksimal"),
                    dbc.Input(id="output-maksimal-input", type="number", placeholder="Jumlah Output Maksimal", className="mb-2"),
                ], md=4),
                dbc.Col([
                    dbc.Label("Good Product Output"),
                    dbc.Input(id="good-product-output-input", type="number", placeholder="Jumlah Good Output", className="mb-2"),
                ], md=4),
                dbc.Col([
                    dbc.Label("Hold & All Defect"),
                    dbc.Input(id="hold-defect-input", type="number", placeholder="Jumlah Defect", className="mb-2"),
                ], md=4),
            ]),
            html.Hr(),
            html.H4("Input Downtime (Opsional)", className="mt-3 mb-3"),
            html.Div(id="downtime-rows-container"),
            dbc.Button("Tambah Downtime", id="add-downtime-row", color="secondary", className="mt-2 mb-4"),
            dbc.Button("Simpan", id="submit-button", color="primary", className="mt-3 w-100"),
            html.Div(id="submit-status", style={"marginTop": "20px", "color": "green"}, className="text-center")
        ])
    ], style={"maxWidth": "900px", "margin": "auto", "marginTop": "30px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"})

def downtime_row(row_id, downtime='', kategori='', workcenter='', proses='', equipment='', start='', finish=''):
    return dbc.Row([
        dbc.Col([
            dbc.Input(id={"type": "start-downtime-input", "index": row_id}, type="text", placeholder="Start (HH:MM)", value=start, className="mb-2"),
        ], md=2),
        dbc.Col([
            dbc.Input(id={"type": "finish-downtime-input", "index": row_id}, type="text", placeholder="Finish (HH:MM)", value=finish, className="mb-2"),
        ], md=2),
        dbc.Col([
            dbc.Input(id={"type": "downtime-downtime-input", "index": row_id}, type="text", placeholder="Downtime", value=downtime, className="mb-2"),
        ], md=2),
        dbc.Col([
            dbc.Input(id={"type": "kategori-downtime-input", "index": row_id}, type="text", placeholder="Kategori", value=kategori, className="mb-2"),
        ], md=2),
        dbc.Col([
            dbc.Input(id={"type": "workcenter-downtime-input", "index": row_id}, type="text", placeholder="Workcenter", value=workcenter, className="mb-2"),
        ], md=1),
        dbc.Col([
            dbc.Input(id={"type": "proses-downtime-input", "index": row_id}, type="text", placeholder="Proses", value=proses, className="mb-2"),
        ], md=1),
        dbc.Col([
            dbc.Input(id={"type": "equipment-downtime-input", "index": row_id}, type="text", placeholder="Equipment", value=equipment, className="mb-2"),
        ], md=1),
        dbc.Col([
            dbc.Button("Hapus", id={"type": "remove-downtime-row", "index": row_id}, color="danger", size="sm", className="mb-2"),
        ], md=1)
    ], id={"type": "downtime-row", "index": row_id}, className="g-1")

@callback(
    Output("downtime-rows-container", "children"),
    Output("downtime-store", "data"),
    Input("add-downtime-row", "n_clicks"),
    Input({"type": "remove-downtime-row", "index": ALL}, "n_clicks"),
    State("downtime-store", "data"),
    State({"type": "start-downtime-input", "index": ALL}, "value"),
    State({"type": "finish-downtime-input", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input", "index": ALL}, "value"),
    State({"type": "proses-downtime-input", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    # Update values
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    # Remove row
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"] == "remove-downtime-row":
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    # Add row
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    # Render rows
    rows = [downtime_row(row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data

@callback(
    Output("submit-status", "children"),
    Input("submit-button", "n_clicks"),
    State("tanggal-input", "value"),
    State("line-input", "value"),
    State("shift-input", "value"),
    State("sku-input", "value"),
    State("loading-time-input", "value"),
    State("output-maksimal-input", "value"),
    State("good-product-output-input", "value"),
    State("hold-defect-input", "value"),
    State("downtime-store", "data"),
    State("user-session", "data"),
    prevent_initial_call=True
)
def save_data(n_clicks, tanggal, line, shift, sku, loading_time, output_maksimal, good_output, hold_defect, downtime_list, user_data):
    if not user_data or not user_data.get("user"):
        return "⚠️ Anda harus login terlebih dahulu."
    user = user_data["user"]
    # Validasi OEE
    if not (tanggal and line and shift and sku and loading_time and output_maksimal and good_output is not None and hold_defect is not None):
        return "⚠️ Harap isi semua field OEE!"
    write_to_gsheet_oee([tanggal, line, shift, sku, loading_time, output_maksimal, good_output, hold_defect, user])
    # Simpan semua downtime
    if downtime_list:
        for row in downtime_list:
            if row.get("downtime") and row.get("kategori") and row.get("workcenter") and row.get("proses") and row.get("equipment") and row.get("start") and row.get("finish"):
                write_to_gsheet_downtime([tanggal, sku, shift, line, row["start"], row["finish"], row["downtime"], row["kategori"], row["workcenter"], row["proses"], row["equipment"], user])
        return "✅ Data OEE & semua downtime berhasil disimpan!"
    return "✅ Data OEE berhasil disimpan!"
