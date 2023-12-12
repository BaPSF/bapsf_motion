__all__ = ["QLogHandler", "QLogger"]

import logging

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
        "NOTSET": logging.NOTSET,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    def __init__(self, logger: logging.Logger, verbosity=logging.WARNING):
        super().__init__()

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
        slider.setMaximum(5)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setTickPosition(slider.TickPosition.TicksBelow)
        slider.setFixedHeight(16)
        slider.setMinimumWidth(100)

        self._slider_widget = slider
        # slider.valueChanged.connect(self.update_log_verbosity())

        label_widgets = []
        for label in self._verbosity.keys():
            lw = QLabel(label)
            lw.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            lw.setMinimumWidth(24)

            font = lw.font()
            font.setPointSize(12)
            lw.setFont(font)

            label_widgets.append(lw)

        row2_layout.addWidget(slider, 0, 1, 1, 8)
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
                fmt="%(asctime)s - [%(levelname)s] %(name)s  %(message)s",
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

        self._logger.info(f"Changed log verbosity to {vkey}.")
