import io
import logging
import logging.config
import multiprocessing
import os
import random
import time
import webbrowser

from dash import Dash, html, dcc, Input, Output, callback, State
from threading import Timer
# from dash_bootstrap_components.themes import DARKLY


class DashStreamHandler(logging.Handler):
    terminator = '\n'

    def __init__(self, level=logging.NOTSET):
        """
        Initialize the handler.

        If stream is not specified, sys.stderr is used.
        """
        super().__init__(level=level)

        self.stream = io.StringIO()
        self._new_log = False

    @property
    def new_log(self) -> bool:
        return self._new_log

    @new_log.setter
    def new_log(self, value):
        self._new_log = value

    def flush(self) -> None:
        """
        Flushes the stream.
        """
        self.acquire()
        try:
            self.stream.flush()
        finally:
            self.release()

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.
            stream.write(msg + self.terminator)
            self.flush()
            self._new_log = True
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)

    def setStream(self, stream):
        """
        Sets the StreamHandler's stream to the specified value,
        if it is different.

        Returns the old stream, if the stream was changed, or None
        if it wasn't.
        """
        if stream is self.stream:
            result = None
        else:
            result = self.stream
            self.acquire()
            try:
                self.flush()
                self.stream = stream
            finally:
                self.release()
        return result

    def __repr__(self):
        level = logging.getLevelName(self.level)
        name = getattr(self.stream, 'name', '')
        #  bpo-36015: name can be an int
        name = str(name)
        if name:
            name += ' '
        return '<%s %s(%s)>' % (self.__class__.__name__, name, level)


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "class": "logging.Formatter",
                "format": "%(asctime)s - [%(levelname)s] %(name)s  %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "dash": {
                "()": DashStreamHandler,
                "level": "DEBUG",
                "formatter": "default",
            },
        },
        "loggers": {
            # "root": {
            #     "level": "DEBUG",
            #     "handlers": ["dash"],
            # },
            ":: GUI ::": {
                "level": "DEBUG",
                "handlers": ["stderr", "dash"],
                "propagate": True,
            },
        },
    },
)
logger = logging.getLogger(":: GUI ::")
for hand in logger.handlers:
    if isinstance(hand, DashStreamHandler):
        handler = hand
        break


ctx = multiprocessing.get_context("fork")
queue = ctx.Queue(10)

app = Dash(
    __name__,
    # external_stylesheets=[DARKLY],
)

app.layout = html.Div(
    children=[
        # html.Div(id="hidden-div", style={"display": "none"}),
        html.Div(
            id="top-row",
            children=[
                html.Div(
                    id="hidden-div", style={"display": "none"},
                ),
                html.H1(
                    "Motion Configuration",
                    style={"text-align": "center", "width": "30%"},
                ),
                html.Button(
                    "DONE",
                    id="done-btn",
                    n_clicks=0,
                    style={
                        "float": "right",
                        "height": "80%",
                        "width": "20%",
                        "margin-left": "auto",
                    },
                ),
            ],
            style={"height": "72px", "display": "flex", "align-items": "center"},
        ),
        # dbc.Row(
        #     children=[
        #         dbc.Col(
        #             html.H1("Motion Configuration", style={"text-align": "center"})
        #         ),
        #         dbc.Col(
        #             dbc.Button(
        #                 "DONE",
        #                 color="primary",
        #                 id="done-btn",
        #                 style={"width": "100%", "height": "60px", "margin": "6px 12px"}
        #             ),
        #             width={"size": 4},
        #             align="center",
        #         ),
        #     ],
        # ),
        # html.H1("Motion Configuration", style={"text-align": "center"}),
        dcc.Tabs(
            id="tabs",
            value="tab-run",
            children=[
                dcc.Tab(label="Run", value="tab-run"),
                dcc.Tab(label="MG Control", value="tab-mg"),
            ],
        ),
        html.Div(id="tab-content"),
        dcc.Interval(id="logging-interval", interval=1000),
        html.Div(
            id="logging-content",
            children=[
                html.Hr(style={"height": "4px", "background-color": "black"}),
                html.H2(
                    "Log",
                    style={"margin": "8px 8px 0px"},
                ),
                dcc.Textarea(
                    id="log",
                    value="",
                    rows=15,
                    readOnly=True,
                    wrap="hard",
                    style={
                        "overflow": "auto",
                        "display": "flex",
                        "flex-direction": "column-reverse",
                        "width": "98%",
                        "margin": "8px",
                    },
                ),
            ],
        ),
    ],
    style={"width": "96vw"}
)


@callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
)
def render_tab_content(tab):
    if tab == "tab-run":
        return render_tab_run()
    elif tab == "tab-mg":
        return html.Div(
            [
                html.H2(
                    "Motion Group Configuration & Control",
                    style={"text-align": "center"},
                ),
            ],
        )


def render_tab_run():
    return html.Div(
        id="run-content",
        children=[
            # html.H2("Run Configuration", style={"text-align": "center"}),
            html.Div(
                children=[
                    html.H3(
                        "TOML Config",
                        style={"text-align": "center", "margin": "4px 0px"}),
                    dcc.Textarea(
                        id="toml-txt",
                        value="",
                        readOnly=False,
                        wrap="soft",
                        draggable=False,
                        style={
                            "overflow": "auto",
                            # "display": "flex",
                            # "flex-direction": "column-reverse",
                            "box-sizing": "border-box",
                            "width": "100%",
                            "height": "600px",
                            "margin": "4px",
                            "resize": "none",
                        },
                    ),
                ],
                style={"width": "50%"},
            )
        ],
    )


@callback(
    Output("log", "value"),
    Input("logging-interval", "n_intervals"),
    State("log", "value"),
)
def update_log(n_intervals, log_text):

    if random.randint(0, 9) in (3, 7):
        logger.info(f"Updating log for the {n_intervals}-th time.")

    if not handler.new_log:
        return log_text

    text = handler.stream.getvalue()
    handler.new_log = False

    return text


@callback(
    Output("hidden-div", "children"),
    Input("done-btn", "n_clicks"),
    State("log", "value")
)
def done(n_clicks, log_text):
    queue.put(log_text)
    return "DONE"


def auto_open_browser(port=8050):
    host = f"http://localhost:{port}"

    if os.environ.get("WERKZEUG_RUN_MAIN", "false") != "true":
        Timer(1, lambda: webbrowser.open_new(host)).start()


def _run(dash):
    port = 8050
    auto_open_browser(port)
    dash.run(
        debug=True,
        port=port,
    )


def run(dash):

    p = ctx.Process(target=_run, args=(dash,))
    p.start()

    print(f"waiting on config - {queue}")
    config = queue.get(block=True)
    print(f"got config {config} - {queue}")

    # time.sleep(5)
    # config = "configuration"

    p.terminate()

    return config

# def _run():
#     port = 8050
#     auto_open_browser(port)
#     app.run(debug=True, port=port)
#
#
# def run():
#     p = multiprocessing.Process(target=_run)
#     p.start()
#
#     # config = queue.get(block=True)
#
#     time.sleep(10)
#     config = "configuration"
#
#     # p.terminate()
#
#     return config
#
#
# if __name__ == "__main__":
#     # _run()
#     run()

if __name__ == "__main__":
    # _run()
    c = run(app)
    print(c)
