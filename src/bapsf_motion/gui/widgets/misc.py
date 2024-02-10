"""This module contains miscellaneous custom Qt widgets."""
__all__ = [
    "IPv4Validator",
    "QLineEditSpecialized",
    "HLinePlain",
    "VLinePlain",
]

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QValidator, QColor
from PySide6.QtWidgets import QLineEdit, QFrame,QWidget

from bapsf_motion.utils import ipv4_pattern as _ipv4_pattern


class IPv4Validator(QValidator):
    def __init__(self, logger=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pattern = _ipv4_pattern

        log_name = "" if logger is None else f"{logger.name}."
        log_name += "IPv4Validator"
        self._logger = logging.getLogger(log_name)

    def validate(self, arg__1: str, arg__2: int) -> object:
        string = arg__1.replace("_", "")

        match = self._pattern.fullmatch(string)
        if match is None:
            self._logger.warning(f"IP address is invalid, '{string}'.")
            return QValidator.State.Intermediate

        return QValidator.State.Acceptable


class QLineEditSpecialized(QLineEdit):
    editingFinishedPayload = Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.editingFinished.connect(self._send_payload)

    def _send_payload(self):
        self.editingFinishedPayload.emit(self)


class HLinePlain(QFrame):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)

        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(3)
        self.setMidLineWidth(3)

        self.set_color(125, 125, 125)

    def setLineWidth(self, arg__1: int):
        super().setLineWidth(arg__1)
        if self.lineWidth() != self.midLineWidth():
            self.setMidLineWidth(arg__1)

    def setMidLineWidth(self, arg__1: int):
        super().setMidLineWidth(arg__1)
        if self.lineWidth() != self.midLineWidth():
            self.setLineWidth(arg__1)

    def set_color(self, r: int, g: int, b: int):
        palette = self.palette()
        palette.setColor(palette.ColorRole.WindowText, QColor(r, g, b))
        self.setPalette(palette)


class VLinePlain(QFrame):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)

        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(3)
        self.setMidLineWidth(3)

        self.set_color(125, 125, 125)

    def setLineWidth(self, arg__1: int):
        super().setLineWidth(arg__1)
        if self.lineWidth() != self.midLineWidth():
            self.setMidLineWidth(arg__1)

    def setMidLineWidth(self, arg__1: int):
        super().setMidLineWidth(arg__1)
        if self.lineWidth() != self.midLineWidth():
            self.setLineWidth(arg__1)

    def set_color(self, r: int, g: int, b: int):
        palette = self.palette()
        palette.setColor(palette.ColorRole.WindowText, QColor(r, g, b))
        self.setPalette(palette)
