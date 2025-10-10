import dash
from dash import html, dcc, Input, Output, State
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import dash_bootstrap_components as dbc
import uuid
from dash.dependencies import ALL

dash.register_page(__name__, path="/input", name="Input Data")

lines = ["1", "1b", "2"]
sku_slots = ["a", "b"]

# create per-line-per-sku downtime stores
stores = []
for ln in lines:
    for sk in sku_slots:
        stores.append(dcc.Store(id=f"downtime-store-{ln}-{sk}"))

layout = dbc.Container(stores + [html.Div(id="input-content")], fluid=True)

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
    # Build a card with a global tanggal and shift, then per-line input blocks
    line_blocks = []
    for ln in lines:
        # Render SKUs as a compact table: two rows (A/B) and columns for the key metrics
        table_header = html.Thead(html.Tr([
            html.Th("SKU"), html.Th("Loading Time (menit)"), html.Th("Output Maksimal"), html.Th("Good Product Output"), html.Th("Hold & All Defect")
        ]))
        table_rows = []
        for sk in sku_slots:
            # display label A/B on the first column but inputs remain the same ids used by callbacks
            label = "A" if sk == "a" else "B"
            table_rows.append(html.Tr([
                html.Td(label),
                html.Td(dbc.Input(id=f"loading-time-input-{ln}-{sk}", type="number", placeholder="480", className="form-control")),
                html.Td(dbc.Input(id=f"output-maksimal-input-{ln}-{sk}", type="number", placeholder="Jumlah Output Maksimal", className="form-control")),
                html.Td(dbc.Input(id=f"good-product-output-input-{ln}-{sk}", type="number", placeholder="Jumlah Good Output", className="form-control")),
                html.Td(dbc.Input(id=f"hold-defect-input-{ln}-{sk}", type="number", placeholder="Jumlah Defect", className="form-control")),
            ]))

        sku_table = dbc.Table([table_header, html.Tbody(table_rows)], bordered=True, hover=False, responsive=True)

        # Also include a small row to input the SKU names (two inputs side-by-side)
        sku_name_row = dbc.Row([
            dbc.Col(dbc.Input(id=f"sku-input-{ln}-a", type="text", placeholder="SKU A", className="mb-2"), md=6),
            dbc.Col(dbc.Input(id=f"sku-input-{ln}-b", type="text", placeholder="SKU B", className="mb-2"), md=6),
        ])

        # Downtime containers and add buttons per sku
        downtime_cols = dbc.Row([
            dbc.Col([html.H6("Downtime SKU A"), html.Div(id=f"downtime-rows-container-{ln}-a"), dbc.Button("Tambah Downtime A", id=f"add-downtime-row-{ln}-a", color="secondary", className="mt-2 mb-3")], md=6),
            dbc.Col([html.H6("Downtime SKU B"), html.Div(id=f"downtime-rows-container-{ln}-b"), dbc.Button("Tambah Downtime B", id=f"add-downtime-row-{ln}-b", color="secondary", className="mt-2 mb-3")], md=6),
        ])

        line_blocks.append(dbc.Card([
            dbc.CardHeader(f"Line {ln}"),
            dbc.CardBody([
                sku_name_row,
                sku_table,
                html.Hr(),
                downtime_cols
            ])
        ], className="mb-3"))

    return dbc.Card([
        dbc.CardBody([
            html.H2("📝 Input Data OEE & Downtime", className="mb-4 mt-2 text-center"),
            dbc.Row([
                dbc.Col([dbc.Label("Tanggal"), dbc.Input(id="tanggal-input", type="text", placeholder="YYYY-MM-DD", className="mb-2")], md=6),
                dbc.Col([dbc.Label("Shift"), dbc.Input(id="shift-input", type="text", placeholder="1/2/3", className="mb-2")], md=6),
            ]),
            html.Div(line_blocks),
            dbc.Button("Simpan Semua Line", id="submit-button", color="primary", className="mt-3 w-100"),
            html.Div(id="submit-status", style={"marginTop": "20px", "color": "green"}, className="text-center")
        ])
    ], style={"maxWidth": "900px", "margin": "auto", "marginTop": "30px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"})

def downtime_row(line, sku_slot, row_id, downtime='', kategori='', workcenter='', proses='', equipment='', start='', finish=''):
    # row_id should be unique
    prefix = f"{line}-{sku_slot}"
    return dbc.Row([
        dbc.Col([dbc.Input(id={"type": f"start-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Start (HH:MM)", value=start, className="mb-2")], md=2),
        dbc.Col([dbc.Input(id={"type": f"finish-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Finish (HH:MM)", value=finish, className="mb-2")], md=2),
        dbc.Col([dbc.Input(id={"type": f"downtime-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Downtime", value=downtime, className="mb-2")], md=2),
        dbc.Col([dbc.Input(id={"type": f"kategori-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Kategori", value=kategori, className="mb-2")], md=2),
        dbc.Col([dbc.Input(id={"type": f"workcenter-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Workcenter", value=workcenter, className="mb-2")], md=1),
        dbc.Col([dbc.Input(id={"type": f"proses-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Proses", value=proses, className="mb-2")], md=1),
        dbc.Col([dbc.Input(id={"type": f"equipment-downtime-input-{prefix}", "index": row_id}, type="text", placeholder="Equipment", value=equipment, className="mb-2")], md=1),
        dbc.Col([dbc.Button("Hapus", id={"type": f"remove-downtime-row-{prefix}", "index": row_id}, color="danger", size="sm", className="mb-2")], md=1)
    ], id={"type": f"downtime-row-{prefix}", "index": row_id}, className="g-1")

@callback(
    Output("downtime-rows-container-1", "children"),
    Output("downtime-store-1", "data"),
    Input("add-downtime-row-1", "n_clicks"),
    Input({"type": "remove-downtime-row-1", "index": ALL}, "n_clicks"),
    State("downtime-store-1", "data"),
    State({"type": "start-downtime-input-1", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
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
        if triggered["type"].endswith("remove-downtime-row-1"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    # Add row
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    # Render rows
    rows = [downtime_row("1", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-1b", "children"),
    Output("downtime-store-1b", "data"),
    Input("add-downtime-row-1b", "n_clicks"),
    Input({"type": "remove-downtime-row-1b", "index": ALL}, "n_clicks"),
    State("downtime-store-1b", "data"),
    State({"type": "start-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1b", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1b", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1b(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-1b"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1b.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("1b", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-2", "children"),
    Output("downtime-store-2", "data"),
    Input("add-downtime-row-2", "n_clicks"),
    Input({"type": "remove-downtime-row-2", "index": ALL}, "n_clicks"),
    State("downtime-store-2", "data"),
    State({"type": "start-downtime-input-2", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-2", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-2", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-2", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-2", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-2", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-2", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_2(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-2"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-2.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("2", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data

# Per-line-per-sku downtime callbacks (1a,1b,1ba,1bb,2a,2b)
@callback(
    Output("downtime-rows-container-1-a", "children"),
    Output("downtime-store-1-a", "data"),
    Input("add-downtime-row-1-a", "n_clicks"),
    Input({"type": "remove-downtime-row-1-a", "index": ALL}, "n_clicks"),
    State("downtime-store-1-a", "data"),
    State({"type": "start-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1-a", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1-a", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1a(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-1-a"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1-a.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("1", "a", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-1-b", "children"),
    Output("downtime-store-1-b", "data"),
    Input("add-downtime-row-1-b", "n_clicks"),
    Input({"type": "remove-downtime-row-1-b", "index": ALL}, "n_clicks"),
    State("downtime-store-1-b", "data"),
    State({"type": "start-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1-b", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1-b", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1b_slot(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-1-b"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1-b.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("1", "b", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-1b-a", "children"),
    Output("downtime-store-1b-a", "data"),
    Input("add-downtime-row-1b-a", "n_clicks"),
    Input({"type": "remove-downtime-row-1b-a", "index": ALL}, "n_clicks"),
    State("downtime-store-1b-a", "data"),
    State({"type": "start-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1b-a", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1b-a", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1ba(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-1b-a"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1b-a.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("1b", "a", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-1b-b", "children"),
    Output("downtime-store-1b-b", "data"),
    Input("add-downtime-row-1b-b", "n_clicks"),
    Input({"type": "remove-downtime-row-1b-b", "index": ALL}, "n_clicks"),
    State("downtime-store-1b-b", "data"),
    State({"type": "start-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-1b-b", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-1b-b", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_1bb(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-1b-b"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-1b-b.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("1b", "b", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-2-a", "children"),
    Output("downtime-store-2-a", "data"),
    Input("add-downtime-row-2-a", "n_clicks"),
    Input({"type": "remove-downtime-row-2-a", "index": ALL}, "n_clicks"),
    State("downtime-store-2-a", "data"),
    State({"type": "start-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-2-a", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-2-a", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_2a(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-2-a"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-2-a.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("2", "a", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data


@callback(
    Output("downtime-rows-container-2-b", "children"),
    Output("downtime-store-2-b", "data"),
    Input("add-downtime-row-2-b", "n_clicks"),
    Input({"type": "remove-downtime-row-2-b", "index": ALL}, "n_clicks"),
    State("downtime-store-2-b", "data"),
    State({"type": "start-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "finish-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "downtime-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "kategori-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "workcenter-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "proses-downtime-input-2-b", "index": ALL}, "value"),
    State({"type": "equipment-downtime-input-2-b", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_downtime_rows_2b(add_click, remove_clicks, downtime_data, start_list, finish_list, downtime_list, kategori_list, workcenter_list, proses_list, equipment_list):
    ctx = dash.callback_context
    if downtime_data is None:
        downtime_data = [{"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''}]
    for i, row in enumerate(downtime_data):
        if i < len(start_list):
            row["start"] = start_list[i]
            row["finish"] = finish_list[i]
            row["downtime"] = downtime_list[i]
            row["kategori"] = kategori_list[i]
            row["workcenter"] = workcenter_list[i]
            row["proses"] = proses_list[i]
            row["equipment"] = equipment_list[i]
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("{" ):
        triggered = eval(ctx.triggered[0]["prop_id"].split(".")[0])
        if triggered["type"].endswith("remove-downtime-row-2-b"):
            downtime_data = [row for row in downtime_data if row["id"] != triggered["index"]]
    elif ctx.triggered and ctx.triggered[0]["prop_id"] == "add-downtime-row-2-b.n_clicks":
        downtime_data.append({"id": str(uuid.uuid4()), "start": '', "finish": '', "downtime": '', "kategori": '', "workcenter": '', "proses": '', "equipment": ''})
    rows = [downtime_row("2", "b", row["id"], row.get("downtime", ''), row.get("kategori", ''), row.get("workcenter", ''), row.get("proses", ''), row.get("equipment", ''), row.get("start", ''), row.get("finish", '')) for row in downtime_data]
    return rows, downtime_data

@callback(
    Output("submit-status", "children"),
    Input("submit-button", "n_clicks"),
    State("tanggal-input", "value"),
    State("shift-input", "value"),
    # Line 1 SKU a
    State("sku-input-1-a", "value"),
    State("loading-time-input-1-a", "value"),
    State("output-maksimal-input-1-a", "value"),
    State("good-product-output-input-1-a", "value"),
    State("hold-defect-input-1-a", "value"),
    State("downtime-store-1-a", "data"),
    # Line 1 SKU b
    State("sku-input-1-b", "value"),
    State("loading-time-input-1-b", "value"),
    State("output-maksimal-input-1-b", "value"),
    State("good-product-output-input-1-b", "value"),
    State("hold-defect-input-1-b", "value"),
    State("downtime-store-1-b", "data"),
    # Line 1b SKU a
    State("sku-input-1b-a", "value"),
    State("loading-time-input-1b-a", "value"),
    State("output-maksimal-input-1b-a", "value"),
    State("good-product-output-input-1b-a", "value"),
    State("hold-defect-input-1b-a", "value"),
    State("downtime-store-1b-a", "data"),
    # Line 1b SKU b
    State("sku-input-1b-b", "value"),
    State("loading-time-input-1b-b", "value"),
    State("output-maksimal-input-1b-b", "value"),
    State("good-product-output-input-1b-b", "value"),
    State("hold-defect-input-1b-b", "value"),
    State("downtime-store-1b-b", "data"),
    # Line 2 SKU a
    State("sku-input-2-a", "value"),
    State("loading-time-input-2-a", "value"),
    State("output-maksimal-input-2-a", "value"),
    State("good-product-output-input-2-a", "value"),
    State("hold-defect-input-2-a", "value"),
    State("downtime-store-2-a", "data"),
    # Line 2 SKU b
    State("sku-input-2-b", "value"),
    State("loading-time-input-2-b", "value"),
    State("output-maksimal-input-2-b", "value"),
    State("good-product-output-input-2-b", "value"),
    State("hold-defect-input-2-b", "value"),
    State("downtime-store-2-b", "data"),
    State("user-session", "data"),
    prevent_initial_call=True
)
def save_data(n_clicks, tanggal, shift,
              sku1a, loading_time1a, output_maksimal1a, good_output1a, hold_defect1a, downtime1a,
              sku1b_slot, loading_time1b_slot, output_maksimal1b_slot, good_output1b_slot, hold_defect1b_slot, downtime1b_slot,
              sku1ba, loading_time1ba, output_maksimal1ba, good_output1ba, hold_defect1ba, downtime1ba,
              sku1bb, loading_time1bb, output_maksimal1bb, good_output1bb, hold_defect1bb, downtime1bb,
              sku2a, loading_time2a, output_maksimal2a, good_output2a, hold_defect2a, downtime2a,
              sku2b, loading_time2b, output_maksimal2b, good_output2b, hold_defect2b, downtime2b,
              user_data):
    if not user_data or not user_data.get("user"):
        return "⚠️ Anda harus login terlebih dahulu."
    user = user_data["user"]
    if not (tanggal and shift):
        return "⚠️ Harap isi Tanggal dan Shift!"

    messages = []

    def save_sku(line_name, sku_label, sku, loading_time, output_maksimal, good_output, hold_defect, downtime_list):
        if not (sku and loading_time and output_maksimal and good_output is not None and hold_defect is not None):
            return f"⚠️ {line_name} {sku_label}: incomplete, skipped."
        write_to_gsheet_oee([tanggal, line_name, shift, sku, loading_time, output_maksimal, good_output, hold_defect, user])
        if downtime_list:
            for row in downtime_list:
                if row.get("downtime") and row.get("kategori") and row.get("workcenter") and row.get("proses") and row.get("equipment") and row.get("start") and row.get("finish"):
                    write_to_gsheet_downtime([tanggal, sku, shift, line_name, row["start"], row["finish"], row["downtime"], row["kategori"], row["workcenter"], row["proses"], row["equipment"], user])
        return f"✅ {line_name} {sku_label} saved."

    messages.append(save_sku("1", "A", sku1a, loading_time1a, output_maksimal1a, good_output1a, hold_defect1a, downtime1a))
    messages.append(save_sku("1", "B", sku1b_slot, loading_time1b_slot, output_maksimal1b_slot, good_output1b_slot, hold_defect1b_slot, downtime1b_slot))
    messages.append(save_sku("1b", "A", sku1ba, loading_time1ba, output_maksimal1ba, good_output1ba, hold_defect1ba, downtime1ba))
    messages.append(save_sku("1b", "B", sku1bb, loading_time1bb, output_maksimal1bb, good_output1bb, hold_defect1bb, downtime1bb))
    messages.append(save_sku("2", "A", sku2a, loading_time2a, output_maksimal2a, good_output2a, hold_defect2a, downtime2a))
    messages.append(save_sku("2", "B", sku2b, loading_time2b, output_maksimal2b, good_output2b, hold_defect2b, downtime2b))

    return html.Ul([html.Li(m) for m in messages])
