"""
A collection of helper functions to assist with the design and
implementation of the package GUIs.
"""

__all__ = ["get_qapplication", "get_color_scheme", "cast_color_to_rgba_string"]

from bapsf_qt.utils import cast_color_to_rgba_string, get_qapplication
from PySide6.QtCore import Qt


def get_color_scheme() -> "Qt.ColorScheme":
    """
    Retrieve the color scheme (light or dark mode) of the operating
    system.  The returns the `~PySide6.QtCore.Qt.ColorScheme` `enum`.
    """
    app = get_qapplication()
    _scheme = app.styleHints().colorScheme()
    return _scheme
