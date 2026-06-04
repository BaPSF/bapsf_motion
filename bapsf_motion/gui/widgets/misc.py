"""This module contains miscellaneous custom Qt widgets."""

__all__ = [
    "BatteryStatusIcon",
    "IPv4Validator",
    "QLineEditSpecialized",
    "QTAIconLabel",
    "HLinePlain",
    "VLinePlain",
    "QDoublePinnedValidator",
]

import ast
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLabel

# import of qtawesome and bapsf_qt must happen after the PySide6 imports
import qtawesome as qta  # noqa
from bapsf_qt.widgets import QLineEditPayload as QLineEditSpecialized  # noqa
from bapsf_qt.widgets import HLinePlain, IPv4Validator, VLinePlain, QTAIconLabel  # noqa


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
        self.setMaximumWidth(self._pixmap_size + 8)
        self.setMaximumHeight(self._pixmap_size + 8)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    def set_battery_status(self, battery_status):
        try:
            _icon = self._icon_map[battery_status]
        except KeyError:
            _icon = self._icon_map["unknown"]

        self.setPixmap(_icon.pixmap(self._pixmap_size, self._pixmap_size))


class QDoublePinnedValidator(QDoubleValidator):
    def fixup(self, input, /):
        min_value = self.bottom()
        max_value = self.top()

        value = ast.literal_eval(input)

        if not isinstance(value, (float, int)):
            return input

        if value < min_value:
            return f"{min_value}"

        if value > max_value:
            return f"{max_value}"
