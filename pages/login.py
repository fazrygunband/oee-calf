import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/login", name="Login")

layout = dbc.Container([
    dcc.Store(id="user-session", storage_type="session"),
    html.H2("🔒 Login User", className="mb-4 mt-2 text-center"),
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Username"),
                    dbc.Input(id="login-username", type="text", placeholder="Username", className="mb-2"),
                ], md=12),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Password"),
                    dbc.Input(id="login-password", type="password", placeholder="Password", className="mb-2"),
                ], md=12),
            ]),
            dbc.Button("Login", id="login-button", color="primary", className="mt-3 w-100"),
            html.Div(id="login-status", className="text-center mt-3", style={"color": "red"})
        ])
    ], style={"maxWidth": "400px", "margin": "auto", "marginTop": "30px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"})
], fluid=True)

# Username & password statis (bisa diganti sesuai kebutuhan)
USERS = {
    "admin": "admin123",
    "user1": "password1",
    "heri":"keju1",
    "dayat":"lead1",
    "latif":"lead2",
    "bowo":"lead3"
}

@callback(
    Output("user-session", "data"),
    Output("login-status", "children"),
    Input("login-button", "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def do_login(n_clicks, username, password):
    if not username or not password:
        return dash.no_update, "Username dan password wajib diisi!"
    if username in USERS and USERS[username] == password:
        return {"user": username}, "Login berhasil!"
    return dash.no_update, "Username atau password salah!"

