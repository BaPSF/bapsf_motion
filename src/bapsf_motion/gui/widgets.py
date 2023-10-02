import logging
import math

from PySide6.QtGui import QValidator
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton, QTextEdit, QPlainTextEdit

from __feature__ import snake_case  # noqa

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
            return QValidator.Intermediate

        return QValidator.Acceptable


class QLogHandler(logging.Handler):
    _log_widget = None  # type: QWidget

    def __init__(self, widget=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_widget = widget

    @property
    def log_widget(self):
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
            self.log_widget.append_plain_text(msg)

    def handle(self, record: logging.LogRecord) -> None:
        self.emit(record)


class LED(QPushButton):
    _aspect_ratio = 1.0
    _on_color = "0ed400"
    _off_color = "0d5800"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_enabled(False)
        self.set_checkable(True)
        self.set_checked(False)

        self.set_fixed_height(24)

    def update_style_sheet(self):
        self.set_style_sheet(self.css)

    def set_fixed_width(self, w: int) -> None:
        super().set_fixed_width(w)
        super().set_fixed_height(round(w / self._aspect_ratio))
        self.update_style_sheet()

    def set_fixed_height(self, h: int) -> None:
        super().set_fixed_height(h)
        super().set_fixed_width(round(self._aspect_ratio * h))
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

        self.set_style_sheet(
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
        style = self.pressed_style if self.is_checked() else self.default_style
        self.set_style_sheet(style)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication([])

    window = QMainWindow()
    _widget = LED()
    window.set_central_widget(_widget)
    window.show()

    app.exec()
