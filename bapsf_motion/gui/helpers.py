"""
A collection of helper functions to assist with the design and
implementation of the package GUIs.
"""
__all__ = ["get_qapplication", "get_color_scheme", "cast_color_to_rgba_string"]

import ast

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from typing import Union


def get_qapplication() -> Union[QApplication, None]:
    """
    Get the current active instance of
    `~PySide6.QtWidgets.QApplication`.  This is a convinces function
    to `~PySide6.QtCore.QCoreApplication.instance`.
    """
    app = QApplication.instance()
    return app


def get_color_scheme() -> "Qt.ColorScheme":
    """
    Retrieve the color scheme (light or dark mode) of the operating
    system.  The returns the `~PySide6.QtCore.Qt.ColorScheme` `enum`.
    """
    app = get_qapplication()
    _scheme = app.styleHints().colorScheme()
    return _scheme


def cast_color_to_rgba_string(color: Union[QColor, str]) -> str:
    """
    Cast ``color`` to an RGBA string representation
    ``'rgba(r, g, b, a)'``

    Parameters
    ----------
    color : Union[QColor, str]
        ``color`` can be an instance of `~PySide6.QtGui.QColor` or a
        string representation of hex, rgb, or rgba color code.  It can
        also be a string representation of a `~PySide6.QtGui.QColor`,
        e.g. ``'QColor(r, g, b)'``.
    """
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
