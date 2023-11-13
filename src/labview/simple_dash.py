import multiprocessing
import os
import time
import webbrowser

from dash import Dash, html, dcc, Input, Output, callback, State
from threading import Timer

ctx = multiprocessing.get_context("fork")
# queue = ctx.Queue()

app = Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1("A Title")
    ],
)


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

    # def _run():
    #     dash.run(debug=True, port=8050)

    p = ctx.Process(target=_run, args=(dash,))
    p.start()
    # p.join()

    # config = queue.get(block=True)

    time.sleep(5)
    config = "configuration"

    p.terminate()

    return config


if __name__ == "__main__":
    # _run()
    c = run(app)
    print(c)
