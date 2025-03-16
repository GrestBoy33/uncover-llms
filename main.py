import dash
from dash import dcc, html, Input, Output, State, MATCH, Patch, ctx
import dash_bootstrap_components as dbc
import threading
import webview
import requests
from ollama_connects import list_available_models, get_ollama_response
import datetime
from sql_connects import (init_db, fetch_all,
                          create_session, update_messages, get_chat_history,
                          delete_session, get_conversation_context,
                          update_session_name, update_private_endpoint,
                          fetch_private_endpoint
                          )


stylesheet1 = './assets/css/style.css'
stylesheet2 = './assets/bWLwgP.css'
bootstrapcss = './assets/bootstrap.css'
fontstylecss = './assets/css/all.css'
response_png = './assets/dice-d6.svg'
user_png = './assets/user.svg'

EXTERNAL_STYLESHEETS = [stylesheet1, stylesheet2, fontstylecss, fontstylecss]

# -------------------------------
# Database Setup (unchanged)
# -------------------------------
init_db()
BETA_EXPIRY_DATE = datetime.datetime(2026, 6, 1)


intro_modal = dbc.Modal(
    [
        dbc.ModalHeader("Welcome to Uncover-LLMs"),
        dbc.ModalBody(
            dcc.Markdown(
                """
                **Welcome to Uncover-LLMs App!**

                Our app empowers you to use AI models privately and securely. You have two main options:

                1. **Offline/Local Mode with Ollama:**  
                  - If you prefer to use AI privately or offline, visit the [Ollama website](https://www.ollama.com) to download your desired version of the AI model.
                  - Once downloaded, select the version from the settings in this app to run AI locally without exposing your data.

                2. **Private Endpoint Mode:**  
                  - Alternatively, you can connect to a private endpoint by setting up your own API and entering the connection details.
                  - This option is ideal for organizations that require complete control over their data and security.

                The objective of Uncover-LLMs App is to provide a flexible platform for leveraging AI models privately—empowering individuals and organizations to secure and control their data while harnessing the power of AI.

                **Please choose your preferred method in the settings to get started.**
                """
            )
        ),
        dbc.ModalFooter(
            dbc.Button("Get Started", id="close-intro", className="ml-auto", n_clicks=0)
        ),
    ],
    id="intro-modal",
    is_open=True,       # Modal is open by default on app load.
    backdrop="static",  # Prevent closing the modal by clicking outside.
    centered=True,
)
private_endpoint_ui = dbc.Form([

    html.Div([
        dbc.Label("Endpoint URL/IP"),
        dbc.Input(id="private-endpoint-url", placeholder="127.0.0.1", type="text")
    ], className="mb-3"),

    html.Div([
        dbc.Label("Port"),
        dbc.Input(id="private-endpoint-port", placeholder="5000", type="number")
    ], className="mb-3"),

    html.Div([
        dbc.Label("Protocol"),
        dcc.Dropdown(
            id="private-endpoint-protocol",
            options=[
                {"label": "HTTP", "value": "http"},
                {"label": "HTTPS", "value": "https"}
            ],
            value="http",
            clearable=False
        ),

    ], className="mb-3"),

    html.Div([
        dbc.Label("API Key / Access Token"),
        dbc.Input(id="private-endpoint-api-key", placeholder="Enter API key", type="password")
    ], id="auth-api-key-container", className="mb-3"),
    dbc.Button("Test", id="test-connection-btn", color="primary", className="mr-2"),
    dbc.Button("Save", id="save-endpoint-btn", color="primary"),
    html.Div(id="connection-output", className="mt-3"),
    html.Div(id="connection-output1", className="mt-3")

], id='private-endpoint-ui')

# -------------------------------
# Dash App Initialization & Layout
# -------------------------------
app = dash.Dash(__name__,
                external_stylesheets=EXTERNAL_STYLESHEETS,
                title='LocaLLMs',
                suppress_callback_exceptions=True

                )

app.layout = dbc.Container([

    dcc.Store(id='session_name_update_flag'),
    dcc.Store(id='private-endpoint-url-store'),
    dcc.Store(id='access-token-store'),
    dcc.Interval(id="session-summary-interval", interval=180000, n_intervals=0),
    dcc.Location(id='url-path'),
    intro_modal,
    dbc.Modal(
        [
            dbc.ModalHeader("Beta Expired"),
            dbc.ModalBody("Beta examination has expired. This app will no longer accepting inputs."),

        ],
        id="beta-modal",
        is_open=False,
        backdrop=True,
        centered=True,
    ),
    # dcc.Store(id='session-store'),
    dbc.Row([
        # Sidebar: Sessions & History
        dbc.Col([
            # html.H5("Logo"),
            dbc.Row([
                html.Img(src="/assets/logo.svg", style={"height": "80px"})
            ], style={"height": "80px"}),

            html.H5("Sessions"),
            dbc.Row([

                dbc.Col(
                    dcc.Dropdown(
                        id='session-dropdown',
                        options=[],
                        value="",
                        clearable=False,
                        style={
                            "width": "100%",
                            "whiteSpace": "normal",  # Allow option text to wrap
                            "wordWrap": "break-word",
                        },
                        # style={
                        #     "width": "100%",
                        #     # "whiteSpace": "normal",
                        #     # "wordWrap": "break-word",
                        #     # "overflow": "auto"
                        # }
                    ),

                    style={"paddingRight": "2px", "paddingLeft": "2px"},
                    width=12
                ),

            ], style={"width": "100%"}),
            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        [html.Img(src="/assets/plus.svg", height="20px", style={"filter": "invert(100%)"})],
                        id="new-session", color="primary",
                    ),
                    width="auto",  # Auto width to fit button size
                    style={'paddingLeft': '0px'}
                ),
                dbc.Col(
                    dbc.Button(
                        [html.Img(src="/assets/trash-can.svg", height="20px", style={"filter": "invert(100%)"})],
                        id="delete-session-button", color="primary",
                    ),
                    width="auto",
                    style={'paddingLeft': '0px', 'paddingRight': '0px'}  # Adds minimum space between buttons
                )], style={'padding': '15px', 'justify-content': 'right'}
            ),

            html.Div(id="session-list", style={"overflowY": "auto"}),
            html.H5("Questions"),
            html.Div(id="history-container", style={"overflowY": "auto"})
        ], width=3, style={"borderRight": "1px solid lightgray", "padding": "15px"}),

        # Chat Section
        dbc.Col([
            dbc.Row([
                dbc.Nav([

                    dbc.Button(
                        html.Img(src="/assets/gear.svg", height="20px", style={"filter": "invert(100%)"}),
                        id="open-offcanvas",
                        color="primary",
                        className="position-fixed end-0  m-3",  # Adjust position
                        style={"zIndex": "1050"}  # Ensure it appears above other elements
                    ),
                    dbc.Offcanvas(
                        html.Div([

                            dbc.Nav([
                                html.Div([
                                    html.Label("Local models"),
                                    dcc.Dropdown(id="model-options", options=[
                                    ], value=[])
                                ], id='local-models'),

                                html.Div([
                                    dbc.Switch(
                                        id="private-endpoint-switch",
                                        label="Connect to private endpoint",
                                        value=False,
                                    ),
                                    html.Div([private_endpoint_ui])
                                ], style={"marginBottom": "15px"}),

                                html.Hr(),

                                # Section 2: Activation Key
                                html.Div([
                                    html.H5("Activation Key"),
                                    dbc.Input(
                                        placeholder="Enter Activation Key",
                                        id="activation-key-input",
                                        type="password",
                                        style={"marginBottom": "10px"}
                                    ),
                                    dbc.Button("Activate", id="activate-key-button", color="primary")
                                ], style={"marginBottom": "15px"}),

                                html.Hr(),
                            ], vertical=True),
                        ]),
                        id="offcanvas",
                        title="Configuration",
                        placement='end',
                        is_open=False,
                        style={
                            "width": "280px",  # Adjusted width
                            "height": "75vh",  # Keeps height less than full screen
                            "margin": "2vh 1vw",  # Adds space from edges (top-bottom & left-right)
                            "borderRadius": "10px",  # Adds rounded corners for a smooth look
                            "boxShadow": "0px 4px 10px rgba(0,0,0,0.1)"  # Adds shadow effect
                        }
                    )
                ])

            ], style={"height": "40px"}),
            dbc.Row([
                html.Div(id="chat-container", style={
                    "height": "80vh", "overflowY": "auto",
                    "border": "1px solid lightgray", "padding": "10px",
                    "borderRadius": "20px"
                })

            ], style={"padding": "40px", "paddingTop": "10px", "paddingBottom": "10px"}),
            dbc.Row([

                html.Div(id='file-output'),

                dbc.Col(
                    dcc.Input(id="user-input", type="text", placeholder="Type a message...", style={"width": "100%"}),
                    width=8),
                dbc.Col([
                    dcc.Upload(children=dbc.Button(
                        [html.Img(src="/assets/upload.svg", height="20px", style={"filter": "invert(100%)"})],
                        id="", n_clicks=0, color="primary", style={"marginLeft": "0px"}), id='upload-file',
                        multiple=False,
                    )

                ], width=1),

                dbc.Col([dbc.Button(
                    [html.Img(src="/assets/circle-up.svg", height="20px", style={"filter": "invert(100%)"})],
                    id="send-button", n_clicks=0, color="primary", style={"marginLeft": "0px"})], width=1),


            ],
                style={"padding": "40px", "paddingTop": "0px"}
                , justify="center"

            ),

            # html.Div(id="loading-indicator", children="", style={"color": "gray", "marginTop": "10px"})
        ], width=9)
    ]),

], fluid=True)


# -------------------------------
# Callback 1: Add New Chat Pair Immediately
# -------------------------------

@app.callback(
    Output("intro-modal", "is_open"),
    Input("close-intro", "n_clicks"),
    State("url-path", "pathname")
)
def close_modal(url_path, is_open):
    if url_path:
        return False
    return is_open
@app.callback(
    Output("private-endpoint-ui", "style"),
    Output("local-models", "style"),
    Input("private-endpoint-switch", "value")
)
def toggle_endpoint_section(switch_value):
    # Check if the "enabled" value is present in the switch.
    if switch_value:
        # If enabled, allow pointer events and full opacity.
        return {"pointerEvents": "auto", "opacity": "1"}, {"pointerEvents": "none", "opacity": "0.5"}
    else:
        # If disabled, prevent interaction and reduce opacity.
        return {"pointerEvents": "none", "opacity": "0.5"}, {"pointerEvents": "auto", "opacity": "1"}


@app.callback(
    Output("connection-output", "children"),
    Input("test-connection-btn", "n_clicks"),
    [State("private-endpoint-url", "value"),
     State("private-endpoint-port", "value"),
     State("private-endpoint-protocol", "value"),
     State("private-endpoint-api-key", "value")]
)
def test_connection(n_clicks, url, port, protocol, api_key):
    if n_clicks:
        # Validate required fields
        if not url or not port or not protocol or not api_key:
            return "Please fill in all fields."
        # Construct the full URL (assuming the test endpoint is '/test')
        full_url = f"{protocol}://{url}:{port}/test"
        api_key = api_key
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.get(full_url, headers=headers, verify=True)
            if response.status_code == 200:
                json_resp = response.json()
                return f"Success: {json_resp.get('message', 'Connected successfully!')}"
            else:
                return f"Error: Received status code {response.status_code}"
        except Exception as e:
            return f"Connection error: {str(e)}"
    return ""


@app.callback(
    Output("connection-output1", "children"),
    Output("private-endpoint-url", "value"),
    Output("private-endpoint-port", "value"),
    Output("private-endpoint-protocol", "value"),
    Output("private-endpoint-api-key", "value"),
    Output("private-endpoint-url-store", "data"),
    Output("access-token-store", "data"),
    Input("save-endpoint-btn", "n_clicks"),
    Input("url-path", "pathname"),
    [
        State("private-endpoint-url", "value"),
        State("private-endpoint-port", "value"),
        State("private-endpoint-protocol", "value"),
        State("private-endpoint-api-key", "value")
    ]
)
def save_endpoint(n_clicks, url_path, url, port, protocol, api_key):
    if n_clicks:
        if not url or not port or not protocol or not api_key:
            return "Please fill in all fields before saving."
        try:
            # Get the current timestamp
            update_private_endpoint(url, port, protocol, api_key)
            full_url = f"{protocol}://{url}:{port}/model"
            return "Endpoint saved successfully!", url, port, protocol, api_key, full_url, api_key
        except Exception as e:
            return (f"Error saving endpoint: {str(e)}", dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                    dash.no_update, dash.no_update)
    else:
        enpoint = fetch_private_endpoint()
        url = enpoint[0][1]
        port = enpoint[0][2]
        protocol = enpoint[0][3]
        api_key = enpoint[0][4]
        full_url = f"{protocol}://{url}:{port}/model"
        return dash.no_update, url, port, protocol, api_key, full_url, api_key


@app.callback(
    Output("model-options", "options"),
    Input('url-path', 'pathname')
)
def update_models_installed(pathname_url):
    models = list_available_models()
    models = [{'label': m, 'value': m} for m in models]

    return models


@app.callback(
    Output("offcanvas", "is_open"),
    Input("open-offcanvas", "n_clicks"),
    State("offcanvas", "is_open"),
    prevent_initial_call=True
)
def toggle_offcanvas(n, is_open):
    return not is_open


@app.callback(
    Output("user-input", "style"),
    Output("beta-modal", "is_open"),
    Input("url-path", "pathname")

)
def check_expiry_block(url_path):
    now = datetime.datetime.now()
    expired = now > BETA_EXPIRY_DATE
    if expired:
        # Even if the user closes the modal, keep inputs disabled.
        return {"pointerEvents": "none", "opacity": "0.5", "width": "100%"}, True
    else:
        return dash.no_update, False


@app.callback(
    [Output("chat-container", "children"),
     Output("history-container", "children"),
     Output("user-input", "value")
     ],
    Input("send-button", "n_clicks"),
    Input("user-input", "n_submit"),
    Input('session-dropdown', 'value'),
    [State("user-input", "value"),
     State("chat-container", "children"),
     State("history-container", "children"),
     ]
)
def add_question(n_clicks, n_clicks_submit, session_id, user_input, chat_history, history):
    # When the user clicks "Send", immediately append a new chat pair
    if n_clicks > 0 and user_input or n_clicks_submit is not None and user_input:
        # Create a new chat pair with pattern-matching IDs using n_clicks as the unique index.
        #         new_pair =    [dbc.Row(f"You: {user_input}", id={"type": "chat-question", "index": n_clicks}, className='question-card-center'),
        # ]
        if n_clicks_submit > n_clicks:
            n_clicks = n_clicks_submit

        patched_children = Patch()

        new_pair = html.Div([
            dbc.Row([
                dbc.Col([html.Img(src=user_png, className='brand-logo')], width=1),
                dbc.Col(
                    html.Div(f"You: {user_input}",
                             id={"type": "chat-question", "index": n_clicks},
                             style={"margin": "10px", "width": "100%"}), width=10
                )
            ]),

            dbc.Row([
                dbc.Col([html.Img(src=response_png, className='brand-logo')], width=1),
                dbc.Col(
                    dcc.Loading(
                        id={'type': 'chat-loading', 'index': n_clicks},
                        children=html.Div(id={'type': 'chat-response', 'index': n_clicks},
                                          style={"margin": "10px", "width": "100%"}
                                          ), type='circle',color="#3F51B5"
                    )
                    # html.Div(id={'type': 'chat-response', 'index': n_clicks},
                    #          style={"marginBottom": "10px", "width": "100%"})

                    , width=10
                )

            ])

        ])
        update_messages(session_id, user_input, 'user')
        # Append new pair to chat-container.

        # if chat_history is None:
        #     chat_history = []
        patched_children.append(new_pair)

        # Also update history (here, simply appending the question).
        new_history = html.Div(f"{user_input}",
                               style={"cursor": "pointer", "borderBottom": "1px solid gray", "padding": "5px"})
        if history is None:
            history = []
        history.append(new_history)

        return patched_children, history, ""
    else:

        rows = get_chat_history(session_id)
        chat_history = []
        history = []
        for sender, message in rows:
            if sender == 'user':
                saved_response = dbc.Row([
                    dbc.Col([html.Img(src=user_png, className='brand-logo')], width=1),
                    dbc.Col(
                        html.Div(f"You: {message}",
                                 # id={"type": "chat-question", "index": n_clicks},
                                 style={"margin": "10px", "width": "100%"}), width=10
                    )
                ])
                chat_history.append(saved_response)
                new_history = html.Div(f"{message}",
                                       style={"margin": "10px", "width": "100%"})
                history.append(new_history)
            else:
                saved_response = dbc.Row([
                    dbc.Col([html.Img(src=response_png, className='brand-logo')], width=1),
                    dbc.Col(
                        html.Div(dcc.Markdown(message),  # Empty response Div to be updated later.
                                 # id={"type": "chat-response", "index": n_clicks},
                                 style={"margin": "10px", "width": "100%"}), width=10
                    )

                ])
                chat_history.append(saved_response)

        return chat_history, history, ""

    return dash.no_update, dash.no_update, dash.no_update


# -------------------------------
# Callback 2: Update Pending Chat Responses Sequentially
# -------------------------------


@app.callback(
    [Output({"type": "chat-response", "index": MATCH}, "children"),
     Output({"type": "chat-loading", "index": MATCH}, "children")],
    Input({"type": "chat-response", "index": MATCH}, "children"),
    [State({"type": "chat-question", "index": MATCH}, "children"),
     State("model-options", "value"),
     State("session-dropdown", "value"),
     State("private-endpoint-switch", "value"),
     State("private-endpoint-url-store", "data"),
     State("access-token-store", "data"),

     ]
)
def update_pending_responses(event, question, model, session_id, model_type, api_url, access_token):
    if question and question != "":
        if model_type:
            model_type = 'api'
        else:
            model_type = 'local'
        context = get_conversation_context(session_id)
        prompt = f"{context}\nUser: {question}\nAI:"
        answer = get_ollama_response(prompt, model, model_type, api_url, access_token)
        update_messages(session_id, answer, 'Ai')
        updated_response = dcc.Markdown(f"**AI:** {answer}", style={'marginBottom': '20px'})
        return "", updated_response
    else:
        return dash.no_update, dash.no_update


@app.callback(
    Output("session_name_update_flag", "data"),
    Input("session-summary-interval", "n_intervals"),
    State('model-options', 'value'),
    State("private-endpoint-switch", "value"),
    State("private-endpoint-url-store", "data"),
    State("access-token-store", "data"),
)
def summarize_sessions(n_intervals, model, model_type, api_url, access_token):
    # Connect to the database
    if n_intervals > 0:
        if model_type:
            model_type = 'api'
        else:
            model_type = 'local'
        sessions = fetch_all()
        updated_sessions = []

        for session in sessions:
            session_id, session_name = session
            # Retrieve conversation context for this session.
            context = get_conversation_context(session_name)
            if context.strip():
                # Build a prompt for summarization.
                # You might want to limit the length of context if too long.
                prompt = f"Summarize the following conversation in 10 words or less:\n{context}"
                summary = get_ollama_response(prompt, model, model_type, api_url, access_token)
                # If we get a valid summary, update the session name.
                if summary and "Error" not in summary:
                    if ':' in summary:
                        summary = summary.split(':')[1]
                    new_name = summary.strip()
                    update_session_name(new_name, session_id)
                    updated_sessions.append((session_id, new_name))

        # For debugging, return a summary of updated sessions.
        return f"Updated sessions: {updated_sessions}"
    else:
        return dash.no_update


@app.callback(
    Output('session-dropdown', 'options'),
    Output('session-dropdown', 'value'),
    Input('new-session', 'n_clicks'),
    Input('delete-session-button', 'n_clicks'),
    Input('url-path', 'pathname'),
    Input("session_name_update_flag", "data"),
    State('session-dropdown', 'value')

)
def create_new_session(n_clicks_add, n_clicks_delete, pathname_url, flag, current_session):
    changed_id = [ctx.triggered[0]['prop_id']]
    if 'new-session.n_clicks' in changed_id:
        rows = fetch_all()
        session_id = f"Session {len(rows) + 1}"
        create_session(session_id)
        rows.append((session_id, session_id))
        return [{'label': r[1], 'value': r[0]} for r in rows], session_id
        # Retrieve all sessions from the DB
    elif 'delete-session-button.n_clicks' in changed_id:
        delete_session(current_session)

        rows = fetch_all()
        return [{'label': r[1], 'value': r[0]} for r in rows], ""

    else:
        rows = fetch_all()
        if len(rows) < 1:
            session_id = f"Session {1}"
            rows.append((session_id, session_id))
        return [{'label': r[1], 'value': r[0]} for r in rows], rows[0][0]


def run_dash():
    # Start Dash (Flask) server; set use_reloader=False to prevent duplicate threads.
    app.run_server(debug=False, use_reloader=False, port=8919)


if __name__ == '__main__':
    dash_thread = threading.Thread(target=run_dash)
    dash_thread.daemon = True  # Allow program to exit even if thread is running.
    dash_thread.start()
    webview.create_window('Uncover-LLMs', 'http://127.0.0.1:8919')
    webview.start()
