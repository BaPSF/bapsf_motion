"""This module contains custom Qt buttons."""
__all__ = [
    "BannerButton",
    "DiscardButton",
    "DoneButton",
    "GearButton",
    "GearValidButton",
    "LED",
    "StopButton",
    "StyleButton",
]

import math

from PySide6.QtCore import QSize
from PySide6.QtGui import QFontMetrics, QColor
from PySide6.QtWidgets import QPushButton
from typing import Optional

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta


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


class BannerButton(StyleButton):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setFixedHeight(48)
        font = self.font()
        font.setPixelSize(24)
        font.setBold(True)
        self.setFont(font)

        _text = self.text()
        self.setText(_text)

    def setText(self, text):
        super().setText(text)
        font = self.font()
        fm = QFontMetrics(font)
        _length = fm.horizontalAdvance(text)
        _padding = 2 * math.ceil(0.5 * (self.height() - fm.height()))
        self.setFixedWidth(_length + _padding)


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
            _text = "Discard && Quit"
        self.setText(_text)


class DoneButton(BannerButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        _text = self.text()
        if _text == "":
            _text = "DONE"
        self.setText(_text)

    def setText(self, text):
        super(StyleButton, self).setText(text)

        font = self.font()
        fm = QFontMetrics(font)
        _length = fm.horizontalAdvance(text)
        _padding = 2 * (self.height() - fm.height())
        self.setFixedWidth(_length + _padding)


class GearButton(StyleButton):
    def __init__(self, color: Optional[str] = None, parent=None):

        try:
            color = cast_color_to_rgba_string(color)
        except (ValueError, TypeError):
            color = None

        if color is None:
            _palette = self.palette()
            _palette_color = _palette.color(_palette.ColorRole.ButtonText)

            _color = self.base_style.get("color", _palette_color)

        super().__init__(
            qta.icon("fa.gear", color=color),
            "",
            parent=parent,
        )

        self._size = 32
        self._icon_size = 24

        self.setFixedWidth(self._size)
        self.setFixedHeight(self._size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))


class GearValidButton(StyleButton):
    def __init__(self, parent=None):
        self._valid_color = QColor(52, 152, 219, a=160)  # "#3498DB"  # blue
        self._invalid_color = QColor(219, 111, 52, a=200)  # "#3498DB" orange

        self._valid_icon = qta.icon("fa.gear", color=self._valid_color)
        self._invalid_icon = qta.icon("fa.gear", color=self._invalid_color)
        self._is_valid = False

        super().__init__(self._invalid_icon, "", parent=parent)

        self._size = 32
        self._icon_size = 24

        self.setFixedWidth(self._size)
        self.setFixedHeight(self._size)
        self.setIconSize(QSize(self._icon_size, self._icon_size))

    def set_valid(self):
        self._is_valid = True
        self._change_validation_icon()

    def set_invalid(self):
        self._is_valid = False
        self._change_validation_icon()

    @property
    def is_valid(self):
        return self._is_valid

    def _change_validation_icon(self):
        _icon = self._valid_icon if self.is_valid else self._invalid_icon
        self.setIcon(_icon)


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


# if __name__ == "__main__":
#     from PySide6.QtWidgets import QApplication, QMainWindow
#
#     app = QApplication([])
#
#     window = QMainWindow()
#     _widget = LED()
#     window.setCentralWidget(_widget)
#     window.show()
#
#     app.exec()
