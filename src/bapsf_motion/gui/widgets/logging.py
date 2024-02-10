"""
This module contains custom Qt widgets for displaying logs generated
by Python's `logging` package.
"""
__all__ = ["QLogHandler", "QLogger"]

import logging
import logging.config

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QTextEdit,
    QPlainTextEdit,
    QWidget,
    QVBoxLayout,
    QLabel,
    QGridLayout,
    QSlider,
    QMainWindow,
    QSizePolicy,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QComboBox,
)
from typing import Union


class QLogHandler(logging.Handler):
    _log_widget = None

    def __init__(self, widget=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_widget = widget

    @property
    def log_widget(self) -> Union[QTextEdit, QPlainTextEdit]:
        return self._log_widget

    @log_widget.setter
    def log_widget(self, value):
        if value is None:
            pass
        elif not isinstance(value, (QTextEdit, QPlainTextEdit)):
            raise TypeError(
                f"Expected an instance of 'QTextEdit' or 'QPlainTextEdit', "
                f"but received type {type(value)}."
            )

        self._log_widget = value

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        print(msg)
        if isinstance(self.log_widget, QTextEdit):
            self.log_widget.append(msg)
        elif isinstance(self.log_widget, QPlainTextEdit):
            self.log_widget.appendPlainText(msg)

    def handle(self, record: logging.LogRecord) -> None:
        self.emit(record)


class QLogger(QWidget):
    _verbosity = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    def __init__(
            self,
            logger: logging.Logger,
            verbosity=logging.WARNING,
            parent=None,
    ):
        super().__init__(parent=parent)

        self._logger = logger  # type: logging.Logger
        self._log_widget = None  # type: QTextEdit
        self._slider_widget = None  # type: QSlider

        self.setLayout(self._define_layout())

        self._handler = self._setup_log_handler()  # type: QLogHandler

        self._slider_widget.valueChanged.connect(self.update_log_verbosity)

    @property
    def handler(self) -> QLogHandler:
        return self._handler

    def _define_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("LOG")
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # second row: verbosity setting
        row2_layout = QGridLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(4)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setTickPosition(slider.TickPosition.TicksBelow)
        slider.setFixedHeight(16)
        slider.setMinimumWidth(100)
        slider.setValue(2)

        self._slider_widget = slider

        label_widgets = []
        for label in self._verbosity.keys():
            lw = QLabel(label)
            lw.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            lw.setMinimumWidth(24)

            font = lw.font()
            font.setPointSize(12)
            lw.setFont(font)

            label_widgets.append(lw)

        row2_layout.addWidget(slider, 0, 1, 1, 6)
        for ii, lw in enumerate(label_widgets):
            row2_layout.addWidget(lw, 1, 2 * ii, 1, 2)

        layout.addLayout(row2_layout)

        # third row: text box
        log_widget = QTextEdit()
        log_widget.setReadOnly(True)
        font = log_widget.font()
        font.setPointSize(10)
        font.setFamily("Courier New")
        log_widget.setFont(font)
        self._log_widget = log_widget

        layout.addWidget(log_widget)

        return layout

    def _setup_log_handler(self):
        handler = QLogHandler(widget=self._log_widget)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - [%(levelname)s] { %(name)s }  %(message)s",
                datefmt="%H:%M:%S",
            ),
        )
        vindex = self._slider_widget.value() - 1
        vkey = list(self._verbosity.keys())[vindex]
        handler.setLevel(self._verbosity[vkey])
        self._logger.addHandler(handler)

        return handler

    def update_log_verbosity(self):
        vindex = self._slider_widget.value() - 1
        vkey = list(self._verbosity.keys())[vindex]

        self.handler.setLevel(self._verbosity[vkey])

        self._logger.info(f"Changed log verbosity to {vkey} ({self._verbosity[vkey]}).")


class DemoQLogger(QMainWindow):
    def __init__(self):
        super().__init__()

        logging.config.dictConfig(self._logging_config_dict)
        self._logger = logging.getLogger(":: GUI ::")

        self._define_main_window()

        self._msg_widget = QLineEdit()
        self._level_widget = QComboBox()

        layout = self._define_layout()

        self._msg_widget.returnPressed.connect(self.enter_log)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    @property
    def _logging_config_dict(self):
        return {
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
            },
            "loggers": {
                "": {  # root logger
                    "level": "WARNING",
                    "handlers": ["stderr", "stdout"],
                    "propagate": True,
                },
                ":: GUI ::": {
                    "level": "DEBUG",
                    "handlers": ["stderr"],
                    "propagate": True,
                },
            },
        }

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def _define_main_window(self):
        self.setWindowTitle("Log Widget Tester")
        self.resize(800, 900)
        self.setMinimumHeight(600)

    def _define_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("DEMO: QLogger")
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        layout.addSpacing(24)

        sublayout = QHBoxLayout()
        label = QLabel("Message:  ")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sublayout.addWidget(label)

        self._msg_widget.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._msg_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sublayout.addWidget(self._msg_widget)

        self._level_widget.addItems(list(QLogger._verbosity.keys()))
        self._level_widget.setEditable(False)
        self._level_widget.setCurrentText(self._level_widget.itemText(0))
        sublayout.addWidget(self._level_widget)

        layout.addLayout(sublayout)

        layout.addSpacing(24)

        # divider
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setMidLineWidth(3)
        layout.addWidget(hline)

        # add logger
        log_widget = QLogger(self.logger)
        log_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.addWidget(log_widget)

        return layout

    def enter_log(self):
        message = self._msg_widget.text()
        lvl_key = self._level_widget.currentText()
        level = QLogger._verbosity[lvl_key]

        self.logger.log(level=level, msg=message)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = DemoQLogger()
    window.show()

    app.exec()
