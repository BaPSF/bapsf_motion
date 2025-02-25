"""This module contains miscellaneous custom Qt widgets."""
__all__ = [
    "BatteryStatusIcon",
    "IPv4Validator",
    "QLineEditSpecialized",
    "QTAIconLabel",
    "HLinePlain",
    "VLinePlain",
]

import logging

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QValidator, QColor, QIcon
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QWidget
from typing import Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.utils import ipv4_pattern as _ipv4_pattern


class QTAIconLabel(QLabel):
    def __init__(self, icon_name, parent=None):
        super().__init__(parent=parent)

        self._icon_name = None
        self._icon = None
        self.setIcon(icon_name)

        self.setFixedSize(32)
        self.setIconSize(28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    @property
    def icon_name(self) -> str:
        return self._icon_name

    @property
    def icon(self) -> QIcon:
        return self._icon

    def _get_icon(self):
        return qta.icon(self._icon_name)

    def setIcon(self, icon_name: str):  # noqa
        try:
            _icon = qta.icon(icon_name)
        except Exception:  # noqa
            return

        self._icon_name = icon_name
        self._icon = _icon

    def setIconSize(self, size: int):  # noqa
        if not isinstance(size, int):
            return
        elif size < 1:
            return

        self.setPixmap(self.icon.pixmap(size, size))

    def setFixedSize(self, size: Union[QSize, int]):
        if isinstance(size, QSize):
            pass
        elif not isinstance(size, int):
            return
        elif size < 1:
            return
        else:
            size = QSize(size, size)

        super().setFixedSize(size)

    def setFixedWidth(self, w):
        self.setFixedSize(w)

    def setFixedHeight(self, h):
        self.setFixedSize(h)


class BatteryStatusIcon(QLabel):
    def __init__(self, parent=None):

        self._pixmap_size = 24
        self._icon_map = {
            "unknown": qta.icon("mdi.microsoft-xbox-controller-battery-unknown"),
            "wired": qta.icon("mdi.microsoft-xbox-controller-battery-charging"),
            "max": qta.icon("mdi.microsoft-xbox-controller-battery-full"),
            "full": qta.icon("mdi.microsoft-xbox-controller-battery-full"),
            "medium": qta.icon("mdi.microsoft-xbox-controller-battery-medium"),
            "low": qta.icon("mdi.microsoft-xbox-controller-battery-low"),
            "empty": qta.icon("mdi.microsoft-xbox-controller-battery-empty"),
        }

        super().__init__("", parent=parent)
        self.setPixmap(
            self._icon_map["unknown"].pixmap(self._pixmap_size, self._pixmap_size)
        )
        self.setMaximumWidth(self._pixmap_size+8)
        self.setMaximumHeight(self._pixmap_size+8)
        self.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

    def set_battery_status(self, battery_status):
        try:
            _icon = self._icon_map[battery_status]
        except KeyError:
            _icon = self._icon_map["unknown"]

        self.setPixmap(_icon.pixmap(self._pixmap_size, self._pixmap_size))


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
