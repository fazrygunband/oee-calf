import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/login", name="Login")

layout = dbc.Container([
    # page-local location replaced by global one in app.py
    # dcc.Location(id="login-redirect"),
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
            dbc.Button("Login", id="login-submit", color="primary", className="mt-3 w-100"),
            html.Div(id="login-status-visible", className="text-center mt-3", style={"color": "red"})
        ])
    ], style={"maxWidth": "400px", "margin": "auto", "marginTop": "30px", "boxShadow": "0 2px 8px rgba(0,0,0,0.08)"})
], fluid=True)

@callback(
    Output("login-button", "n_clicks"),
    Input("login-submit", "n_clicks"),
    State("login-button", "n_clicks"),
    prevent_initial_call=True
)
def proxy_login_click(submit_clicks, current):
    # proxy the visible page button to the hidden global login-button
    if not submit_clicks:
        raise dash.exceptions.PreventUpdate
    return (current or 0) + 1


# Mirror the global hidden login-status into the page-local visible status div
@callback(
    Output("login-status-visible", "children"),
    Input("login-status", "children")
)
def mirror_login_status(global_status):
    # simply mirror the global status into the visible component
    return global_status or ""


@callback(
    Output("global-login-username", "value"),
    Output("global-login-password", "value"),
    Input("login-username", "value"),
    Input("login-password", "value"),
    Input("login-submit", "n_clicks"),
    State("global-login-username", "value"),
    State("global-login-password", "value"),
)
def sync_global_inputs(local_username, local_password, submit_clicks, cur_user, cur_pass):
    """Keep the hidden global login inputs in sync with the visible page inputs.

    This single callback owns both outputs so Dash won't complain about duplicate
    outputs. It simply mirrors the current local values into the globals.
    """
    # Prefer explicit local values when available
    new_user = local_username if local_username is not None else (cur_user or "")
    new_pass = local_password if local_password is not None else (cur_pass or "")
    return new_user, new_pass

# Authentication handled centrally in app.py (combined login/logout callback)
