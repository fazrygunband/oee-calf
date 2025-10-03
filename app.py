import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, callback

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
server = app.server

app.layout = dbc.Container(
    [
        dcc.Store(id="user-session", storage_type="session"),
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Dashboard", href="/")),
                dbc.NavItem(dbc.NavLink("Input Data", href="/input")),
                dbc.NavItem(dbc.NavLink("Login", href="/login")),
            ],
            brand="📊 OEE Monitoring",
            color="dark",
            dark=True,
            fluid=True
        ),
        dash.page_container   # semua page dari folder /pages ditampilkan di sini
    ],
    fluid=True
)
