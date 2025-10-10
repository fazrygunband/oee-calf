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

# Static users (same credentials used in pages/login.py)
USERS = {
    "admin": "admin123",
    "user1": "password1",
    "heri": "heri2024",
    "dayat": "dayat2024",
    "latif": "latif2024",
    "bowo": "bowo2024"
}

app.layout = dbc.Container(
    [
        dcc.Store(id="user-session", storage_type="session"),
    # Global location and status used by the centralized auth callback
    dcc.Location(id="login-redirect"),
    html.Div(id="login-status", style={"display": "none"}),
    # Hidden global inputs for username/password so callbacks that use them as State won't fail
    dcc.Input(id="global-login-username", type="text", style={"display": "none"}),
    dcc.Input(id="global-login-password", type="password", style={"display": "none"}),
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Dashboard", href="/")),
                dbc.NavItem(dbc.NavLink("Input Data", href="/input")),
                dbc.NavItem(dbc.NavLink("Login", href="/login")),
                # Persistent nav-user container with username span and a hidden logout button
                html.Div([
                    html.Span(id="nav-username", style={"color": "white", "marginRight": "10px", "fontWeight": "600"}),
                    dbc.Button("Logout", id="logout-button", color="light", size="sm", style={"display": "none"}),
                    # Hidden global login button (proxy target) so callbacks referencing "login-button" always find the component
                    html.Button(id="login-button", style={"display": "none"}),
                ], id="nav-user", style={"marginLeft": "auto", "display": "flex", "alignItems": "center", "gap": "8px"}),
            ],
            brand=html.Div([
                html.Img(src=app.get_asset_url('logo.png'), height="80px", style={"marginRight": "12px", "verticalAlign": "middle", "backgroundColor": "white", "padding": "6px", "borderRadius": "8px"}),
                html.Span("OEE Monitoring", style={"verticalAlign": "middle", "fontWeight": "600", "color": "#ffffff"})
            ], style={"display": "flex", "alignItems": "center"}),
            color="dark",
            dark=True,
            fluid=True
        ),
        dash.page_container   # semua page dari folder /pages ditampilkan di sini
    ],
    fluid=True
)


# Update nav username text and logout button visibility based on session store
@callback(
    Output("nav-username", "children"),
    Output("logout-button", "style"),
    Input("user-session", "data")
)
def update_nav_user(session_data):
    # default: hide logout button and clear username
    hidden_style = {"display": "none"}
    if session_data and session_data.get("user"):
        user = session_data.get("user")
        return f"{user}", {"display": "inline-flex"}
    return "", hidden_style


# Note: logout is handled in the combined auth callback (`handle_auth`) below


# Combined login/logout handler to avoid duplicate outputs on user-session
@callback(
    Output("user-session", "data"),
    Output("login-status", "children"),
    Output("login-redirect", "pathname"),
    Input("login-button", "n_clicks"),
    Input("logout-button", "n_clicks"),
    State("global-login-username", "value"),
    State("global-login-password", "value"),
    prevent_initial_call=True
)
def handle_auth(login_click, logout_click, username, password):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # Logout pressed
    if trigger == "logout-button":
        return {}, dash.no_update, "/login"

    # Login pressed
    if trigger == "login-button":
        if not username or not password:
            return dash.no_update, "Username dan password wajib diisi!", dash.no_update
        if username in USERS and USERS[username] == password:
            return {"user": username}, "Login berhasil!", "/"
        return dash.no_update, "Username atau password salah!", dash.no_update
    return dash.no_update, dash.no_update, dash.no_update
