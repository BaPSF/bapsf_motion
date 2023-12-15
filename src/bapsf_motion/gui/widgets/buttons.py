__all__ = ["LED", "StopButton", "StyleButton"]

import math

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize


class LED(QPushButton):
    _aspect_ratio = 1.0
    _on_color = "0ed400"
    _off_color = "0d5800"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


class StyleButton(QPushButton):
    _default_base_style = {
            "border-radius": "6px",
            "border": "0px",
            "background-color": "rgb(95, 95, 95)",
        }
    _default_hover_style = {}
    _default_pressed_style = {"background-color": "rgb(117, 117, 117)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._base_style = {**self._default_base_style}
        self._hover_style = {**self._default_hover_style}
        self._pressed_style = {**self._default_pressed_style}

        self._resetStyleSheet()

    @property
    def _style(self):
        _base = "; ".join([f"{k}: {v}" for k, v in self.base_style.items()])
        _hover = "; ".join([f"{k}: {v}" for k, v in self.hover_style.items()])
        _pressed = "; ".join([f"{k}: {v}" for k, v in self.pressed_style.items()])
        return f"""
        StyleButton {{ {_base} }}
        
        StyleButton:hover {{ {_hover}  }}
        
        StyleButton:pressed {{ {_pressed} }}
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

    def _resetStyleSheet(self):
        self.setStyleSheet(self._style)

    def update_style_sheet(self, styles, action="base", reset=False):

        if action not in ("base", "hover", "pressed"):
            return

        if action == "base":
            _style = self.base_style if not reset else {**self._default_base_style}
        elif action == "hover":
            _style = self.hover_style if not reset else {**self._default_hover_style}
        else:  # action == "pressed":
            _style = self.pressed_style if not reset else {**self._default_pressed_style}

        new_style = {**_style, **styles}

        if action == "base":
            self._base_style = new_style
        elif action == "hover":
            self._hover_style = new_style
        else:  # action == "pressed"
            self._pressed_style = new_style

        self._resetStyleSheet()


class StopButton(QPushButton):
    default_style = """
    background-color: rgb(255,90,90);
    border-radius: 6px;
    border: 2px solid black;
    """
    pressed_style = """
    background-color: rgb(90,255,90)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.set_style_sheet(self.default_style)
        # self.set_checkable(True)

        self.setStyleSheet(
            """
        StopButton {
          background-color: rgb(255,130,130);
          border-radius: 6px;
          border: 1px solid black;
        }

        StopButton:hover {
          border: 3px solid black;
          background-color: rgb(255,70,70);
        }
        """
        )

        # self.pressed.connect(self.toggle_style)
        # self.released.connect(self.toggle_style)

    def toggle_style(self):
        style = self.pressed_style if self.isChecked() else self.default_style
        self.setStyleSheet(style)


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
