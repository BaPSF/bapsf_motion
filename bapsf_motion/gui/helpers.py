"""
A collection of helper functions to assist with the design and
implementation of the package GUIs.
"""

__all__ = ["get_qapplication", "get_color_scheme", "cast_color_to_rgba_string"]

import ast

from bapsf_qt.utils import cast_color_to_rgba_string
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
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
