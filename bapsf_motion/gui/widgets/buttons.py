"""This module contains custom Qt buttons."""

__all__ = [
    "AutoScaleButton",
    "DiscardButton",
    "DoneButton",
    "EnableIndicator",
    "GearButton",
    "GearValidButton",
    "IconButton",
    "LED",
    "StopButton",
    "StyleButton",
    "ValidButton",
    "ZeroButton",
]

import math

from bapsf_qt.buttons import (
    AutoScaleButton,
    DiscardButton,
    DoneButton,
    GearButton,
    GearValidButton,
    IconButton,
    StyleButton,
    StopButton,
    ValidButton,
    ZeroButton,
)
from PySide6.QtCore import QSize, Slot
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QPushButton
from typing import Optional, Union

from bapsf_motion.gui.helpers import cast_color_to_rgba_string
from bapsf_motion.gui.icons import icon_name_dict

# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta  # noqa


class LED(QPushButton):
    _aspect_ratio = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._on_color = "0ed400"  # rgb(14, 212, 0)
        self._off_color = "0d5800"  # rgb(13, 88, 0)

        self.setEnabled(False)
        self.setCheckable(True)
        self.setChecked(False)

        self.set_fixed_height(24)

    def update_style_sheet(self):
        self.setStyleSheet(self.css)

    def set_fixed_width(self, w: int) -> None:
        super().setFixedWidth(w)
        super().setFixedHeight(round(w / self._aspect_ratio))
        self.update_style_sheet()

    def set_fixed_height(self, h: int) -> None:
        super().setFixedHeight(h)
        super().setFixedWidth(round(self._aspect_ratio * h))
        self.update_style_sheet()

    def set_fixed_size(self, arg__1: QSize) -> None:
        raise NotImplementedError(
            "This method is not available, use 'set_fixed_width' or "
            "'set_fixed_height' instead. "
        )

    @property
    def on_color(self):
        return self._on_color

    @on_color.setter
    def on_color(self, color: str):
        self._on_color = color
        self.update_style_sheet()

    @property
    def off_color(self):
        return self._off_color

    @off_color.setter
    def off_color(self, color: str):
        self._off_color = color
        self.update_style_sheet()

    @property
    def css(self):
        radius = 0.5 * min(self.size().width(), self.size().height())
        border_thick = math.floor(2.0 * radius / 10.0)
        if border_thick == 0:
            border_thick = 1
        elif border_thick > 5:
            border_thick = 5

        radius = math.floor(radius)

        return f"""
        LED {{
            border: {border_thick}px solid black;
            border-radius: {radius}px;
            background-color: QRadialGradient(
                cx:0.5,
                cy:0.5,
                radius:1.1,
                fx:0.4,
                fy:0.4,
                stop:0 #{self._off_color},
                stop:1 rgb(0,0,0)); 
        }}

        LED:checked {{
            background-color: QRadialGradient(
                cx:0.5,
                cy:0.5,
                radius:0.8,
                fx:0.4,
                fy:0.4,
                stop:0 #{self._on_color},
                stop:0.25 #{self._on_color},
                stop:1 rgb(0,0,0)); 
        }}
        """


class EnableIndicator(StyleButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._enabled_text = "ENABLED"
        self._disabled_text = "DISABLED"

        # define styles
        self.update_style_sheet(
            styles={"background-color": "rgb(250, 66, 45)"},
            action="base",
        )
        self.update_style_sheet(
            styles={"background-color": "rgb(52, 161, 219)"},
            action="checked",
        )

        self.setCheckable(True)
        self.setChecked(False)

        self.clicked.connect(self._maintain_check_state)

    def setChecked(self, arg__1):
        super().setChecked(arg__1)

        _text = self._enabled_text if arg__1 else self._disabled_text
        self.setText(_text)

    @Slot()
    def _maintain_check_state(self):
        # do not allow button clicks to change check state
        _state = self.isChecked()
        self.setChecked(not _state)
