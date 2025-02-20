__all__ = ["get_qapplication", "get_color_scheme", "cast_color_to_rgba_string"]

import ast

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from typing import Union


def get_qapplication() -> Union[QApplication, None]:
    app = QApplication.instance()
    return app


def get_color_scheme() -> "Qt.ColorScheme":
    app = get_qapplication()
    _scheme = app.styleHints().colorScheme()
    return _scheme


def cast_color_to_rgba_string(color: Union[QColor, str]) -> str:
    if isinstance(color, QColor):
        pass
    elif not isinstance(color, str):
        raise TypeError(f"Color {color} is not a valid type, expect str or QColor.")
    elif color.startswith("QColor"):
        color = eval(color)
    elif color.startswith("#"):
        color = QColor(color)
    elif color.startswith("rgba"):
        args = ast.literal_eval(color[4:])
        color = QColor(*args)
    elif color.startswith("rgb"):
        args = ast.literal_eval(color[3:])
        color = QColor(*args)
        color.setAlpha(255)
    else:
        raise ValueError("Unable to cast color {color}.")

    return f"rgba{color.getRgb()}"
