"""This module contains custom Qt buttons."""
__all__ = [
    "BannerButton",
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

from PySide6.QtCore import QSize
from PySide6.QtGui import QFontMetrics, QColor, QIcon, QFont
from PySide6.QtWidgets import QPushButton
from typing import Optional, Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.gui.helpers import cast_color_to_rgba_string


class StyleButton(QPushButton):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._default_base_style = {
            "border-radius": "4px",
            f"border": f"2px solid rgb(123, 123, 123)",
            "background-color": "rgb(163, 163, 163)",
            "color": "rgb(50, 50, 50)",
        }
        self._default_hover_style = {}
        self._default_pressed_style = {"background-color": "rgb(111, 111, 111)"}
        self._default_checked_style = {}
        self._default_disabled_style = {"color": "rgb(123, 123, 123)"}

        self._base_style = {**self._default_base_style}
        self._hover_style = {**self._default_hover_style}
        self._pressed_style = {**self._default_pressed_style}
        self._checked_style = {**self._default_checked_style}
        self._disabled_style = {**self._default_disabled_style}

        _font = self.font()
        _font.setBold(True)
        self.setFont(_font)

        self._resetStyleSheet()

    @property
    def _style(self):
        _cls_name = self.__class__.__name__
        _base = "; ".join([f"{k}: {v}" for k, v in self.base_style.items()])
        _hover = "; ".join([f"{k}: {v}" for k, v in self.hover_style.items()])
        _pressed = "; ".join([f"{k}: {v}" for k, v in self.pressed_style.items()])
        _checked = "; ".join([f"{k}: {v}" for k, v in self.checked_style.items()])
        _disabled = "; ".join([f"{k}: {v}" for k, v in self.disabled_style.items()])

        # _style = self.style()
        # _palette = _style.standardPalette()
        # _style_color = _palette.color(self.palette().ColorRole.ButtonText)
        #
        # Determine text color and transparency for the disabled state
        # try:
        #     color = self.base_style["color"]
        # except KeyError:
        #     color = _style_color
        #
        # if isinstance(color, QColor):
        #     pass
        # elif not isinstance(color, str):
        #     color = _style_color
        # elif color.startswith("QColor"):
        #     color = eval(color)
        # elif color.startswith("#"):
        #     color = QColor(color)
        # elif color.startswith("rgba"):
        #     args = ast.literal_eval(color[4:])
        #     color = QColor(*args)
        # elif color.startswith("rgb"):
        #     args = ast.literal_eval(color[3:])
        #     color = QColor(*args)
        # else:
        #     color = _style_color
        #
        # color.setAlpha(100)
        # disable_string = f"color: rgba{color.getRgb()}"

        return f"""
        {_cls_name} {{ {_base} }}

        {_cls_name}:hover {{ {_hover}  }}

        {_cls_name}:pressed {{ {_pressed} }}

        {_cls_name}:checked {{ {_checked} }}
        
        {_cls_name}:disabled {{ {_disabled} }}
        """

    @property
    def base_style(self):
        return self._base_style

    @property
    def hover_style(self):
        return self._hover_style

    @property
    def pressed_style(self):
        return self._pressed_style

    @property
    def checked_style(self):
        return self._checked_style

    @property
    def disabled_style(self):
        return self._disabled_style

    def _resetStyleSheet(self):
        self.setStyleSheet(self._style)

    def setPointSize(self, point_size):
        font = self.font()
        font.setPointSize(point_size)
        self.setFont(font)

    def update_style_sheet(self, styles, action="base", reset=False):

        if action not in ("base", "hover", "pressed", "checked", "disabled"):
            return

        if action == "base":
            _style = self.base_style if not reset else {**self._default_base_style}
            self._base_style = {**_style, **styles}
        elif action == "hover":
            _style = self.hover_style if not reset else {**self._default_hover_style}
            self._hover_style = {**_style, **styles}
        elif action == "pressed":
            _style = self.pressed_style if not reset else {**self._default_pressed_style}
            self._pressed_style = {**_style, **styles}
        elif action == "checked":
            _style = self.pressed_style if not reset else {**self._default_checked_style}
            self._checked_style = {**_style, **styles}
        else:  # action == "disabled
            _style = (
                self.disabled_style if not reset
                else {**self._default_disabled_style}
            )
            self._disabled_style = {**_style, **styles}

        self._resetStyleSheet()


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


class BannerButton(StyleButton):

    def __init__(self, *args, **kwargs):
        self._max_font_height_ratio = 0.8

        super().__init__(*args, **kwargs)

        self.setFixedHeight(48)
        font = self.font()
        font.setPixelSize(24)
        font.setBold(True)
        self.setFont(font)

        _text = self.text()
        self.setText(_text)

    def _calculate_target_width(self, text: str = None, scale: float = 1.0):
        if text is None:
            text = self.text()

        font = self.font()
        fm = QFontMetrics(font)
        _length = fm.horizontalAdvance(text)
        _padding = 2 * math.ceil(0.5 * scale * (self.height() - fm.height()))
        return _length + _padding

    def setText(self, text):
        super().setText(text)

        # allow larger width than the one calculated
        new_width = self._calculate_target_width(text)
        width = new_width if new_width >= self.width() else self.width()
        self.setFixedWidth(width)

    def setFont(self, font: QFont):
        ratio = font.pointSize() / self.height()
        if ratio > self._max_font_height_ratio:
            # automatically shrink font if too large for height
            font_size = math.floor(self._max_font_height_ratio * self.height())
            font.setPointSize(font_size)
        super().setFont(font)

        _txt = self.text()
        self.setText(_txt)

    def setFixedHeight(self, h):
        ratio = self.font().pixelSize() / h
        if ratio > self._max_font_height_ratio:
            # automatically shrink font if too large for given height
            font_size = math.floor(self._max_font_height_ratio * h)
            font = self.font()
            font.setPointSize(font_size)
            self.setFont(font)

        super().setFixedHeight(h)
        _txt = self.text()
        self.setText(_txt)

    def shrink_width(self, scale: float = 1.0):
        target_width = self._calculate_target_width(scale=scale)
        self.setFixedWidth(target_width)


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
        self._icon = qta.icon("fa.gear", color=icon_color)
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

    def _enforce_checked_state(self):
        self.setChecked(self.is_valid)


class GearValidButton(ValidButton):
    def __init__(self, parent=None):
        self._valid_color = QColor(52, 161, 219, 240)
        self._invalid_color = QColor(250, 66, 45, 200)

        self._valid_icon = qta.icon("fa.gear", color=self._valid_color)
        self._invalid_icon = qta.icon("fa.gear", color=self._invalid_color)
        self._disabled_icon = qta.icon("fa.gear")

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

    def _maintain_check_state(self):
        # do not allow button clicks to change check state
        _state = self.isChecked()
        self.setChecked(not _state)
