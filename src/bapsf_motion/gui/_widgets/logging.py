__all__ = ["QLogHandler"]

import logging

from PySide6.QtWidgets import (
    QTextEdit,
    QPlainTextEdit,
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
