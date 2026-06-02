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

from bapsf_qt.buttons import AutoScaleButton
from bapsf_qt.buttons import StyleButton
from PySide6.QtCore import QSize, Slot
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon
from PySide6.QtWidgets import QPushButton
from typing import Optional, Union

from bapsf_motion.gui.helpers import cast_color_to_rgba_string
from bapsf_motion.gui.icons import icon_name_dict

# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta  # noqa


class IconButton(StyleButton):
    def __init__(
        self,
        qta_icon_name: str,
        *args,
        color: Union[QColor, str, None] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        try:
            color = cast_color_to_rgba_string(color)
        except (ValueError, TypeError):
            color = None

        if color is None:
            _palette = self.palette()
            _palette_color = _palette.color(_palette.ColorRole.ButtonText)

            color = self.base_style.get("color", _palette_color)

        if not isinstance(color, QColor):
            color = cast_color_to_rgba_string(color)
            icon_color = color.replace("rgba(", "").replace(")", "")
            r, g, b, a = map(int, icon_color.split(","))
            icon_color = QColor(r, g, b, a=a)
        else:
            icon_color = color

        self.update_style_sheet(styles={"color": color}, action="base")
        self._icon = qta.icon(qta_icon_name, color=icon_color)

        self.setIcon(self._icon)

    @property
    def icon(self) -> QIcon:
        return self._icon

    def setIconSize(self, size: Union[QSize, int]):
        if isinstance(size, int):
            size = QSize(size, size)

        if not isinstance(size, QSize):
            return

        super().setIconSize(size)


BannerButton = AutoScaleButton


class DiscardButton(BannerButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_style_sheet(
            styles={
                "background-color": "rgb(232, 80, 74)",
                "color": "rgb(30, 30, 30)",
            },
            action="base",
        )
        self.update_style_sheet(
            styles={"background-color": self._default_base_style["background-color"]},
            action="disabled",
        )

        _text = self.text()
        if _text == "":
            _text = "Discard"
        self.setText(_text)


class DoneButton(BannerButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        _text = self.text()
        if _text == "":
            _text = "DONE"
        self.setText(_text)

    def _calculate_target_width(self, text: str = None, scale: float = 1.0):
        scale = 2 * scale
        return super()._calculate_target_width(text, scale=scale)


class GearButton(StyleButton):
    def __init__(self, color: Optional[str] = None, parent=None):
        super().__init__(parent=parent)

        try:
            color = cast_color_to_rgba_string(color)
        except (ValueError, TypeError):
            color = None

        if color is None:
            _palette = self.palette()
            _palette_color = _palette.color(_palette.ColorRole.ButtonText)

            color = self.base_style.get("color", _palette_color)

        if not isinstance(color, QColor):
            color = cast_color_to_rgba_string(color)
            icon_color = color.replace("rgba(", "").replace(")", "")
            r, g, b, a = map(int, icon_color.split(","))
            icon_color = QColor(r, g, b, a=a)
        else:
            icon_color = color

        self.update_style_sheet(styles={"color": color}, action="base")
        self._icon = qta.icon(icon_name_dict["gear"], color=icon_color)
        self.setIcon(self._icon)

        self._size = 32
        self._icon_size = 24

        self.setFixedWidth(self._size)
        self.setFixedHeight(self._size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))


class ValidButton(StyleButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._is_valid = False

        self.update_style_sheet(
            styles={"background-color": "rgb(95, 95, 95)"},
            action="pressed",
        )
        self.update_style_sheet(
            styles={"background-color": "rgb(123, 123, 123)"},
            action="checked",
        )  # checked state is the valid state

        self.setCheckable(True)
        self.clicked.connect(self._enforce_checked_state)

    @property
    def is_valid(self):
        return self._is_valid

    def setCheckable(self, arg__1):
        super().setCheckable(True)

    def set_valid(self, state: bool = True):
        self.setChecked(state)
        self._is_valid = state

    def set_invalid(self):
        self.set_valid(False)

    @Slot()
    def _enforce_checked_state(self):
        self.setChecked(self.is_valid)


class GearValidButton(ValidButton):
    def __init__(self, parent=None):
        self._valid_color = QColor(52, 161, 219, 240)
        self._invalid_color = QColor(250, 66, 45, 200)

        icon_name = icon_name_dict["gear"]
        self._valid_icon = qta.icon(icon_name, color=self._valid_color)
        self._invalid_icon = qta.icon(icon_name, color=self._invalid_color)
        self._disabled_icon = qta.icon(icon_name)

        super().__init__(self._invalid_icon, "", parent=parent)

        self.update_style_sheet(
            styles={"background-color": "rgb(95, 95, 95)"},
            action="pressed",
        )
        self.update_style_sheet(
            styles={"background-color": "rgb(123, 123, 123)"},
            action="checked",
        )  # checked state is the valid state

        self.setIcon(self._invalid_icon)

        self._size = None
        self.setFixedSize(32)

        self._icon_size = None
        self.setIconSize(28)

        self.setChecked(False)

    def set_valid(self, state: bool = True):
        _icon = self._valid_icon if state else self._invalid_icon
        self.setIcon(_icon)
        super().set_valid(state=state)

    def set_invalid(self):
        self.setIcon(self._invalid_icon)
        super().set_invalid()

    def setIconSize(self, size: int):
        if not isinstance(size, int):
            return
        elif size <= 0:
            return

        self._icon_size = size
        size = QSize(size, size)
        super().setIconSize(size)

    def setFixedSize(self, size: int):
        if not isinstance(size, int):
            return
        elif size <= 0:
            return

        self._size = size
        size = QSize(size, size)
        super().setFixedSize(size)

    def setFixedHeight(self, h):
        self.setFixedSize(h)

    def setFixedWidth(self, w):
        self.setFixedSize(w)

    def _change_validation_icon(self):
        _icon = self._valid_icon if self.is_valid else self._invalid_icon
        self.setIcon(_icon)

    def setDisabled(self, arg__1):
        self.setEnabled(not arg__1)

    def setEnabled(self, arg__1):
        self.set_invalid()
        if not arg__1:
            self.setIcon(self._disabled_icon)

        super().setEnabled(arg__1)


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


class StopButton(StyleButton):
    def __init__(self, *args, **kwargs):
        super().__init__("STOP", *args, **kwargs)

        self.update_style_sheet(
            styles={
                "background-color": "rgb(232, 80, 74)",
                "border-radius": "6px",
                "border": "3px solid rgb(90, 90, 90)",
                "color": "rgba(30, 30, 30, 240)",
            },
            action="base",
        )
        self.update_style_sheet(
            styles={
                "border": "3px solid rgb(255, 0, 0)",
                "background-color": "rgb(255, 70, 70)",
            },
            action="hover",
        )


class ZeroButton(StyleButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_style_sheet(
            styles={"background-color": "rgb(52, 161, 219)"},
            action="pressed",
        )


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
