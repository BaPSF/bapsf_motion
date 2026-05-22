__all__ = ["BaseCalculatorApp", "BaseCalculatorWindow"]
from abc import ABC, abstractmethod
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QMainWindow
from typing import Type


class BaseCalculatorWindow(QMainWindow):
    closing = Signal()

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)


class BaseCalculatorApp(QApplication):
    _CALCULATOR_CLASS = NotImplemented  # type: Type[BaseCalculatorWindow]

    def __init__(self, *args, **kwargs):

        if not issubclass(self._CALCULATOR_CLASS, BaseCalculatorWindow):
            raise TypeError(
                f"The defined class attribute _CALCULATOR_CLASS is not "
                f"a subclass of {BaseCalculatorWindow.__module__}."
                f"{BaseCalculatorWindow.__name__}"
            )

        super().__init__(*args, **kwargs)

        self.setStyle("Fusion")
        self.styleHints().setColorScheme(Qt.ColorScheme.Light)

        self._window = self._CALCULATOR_CLASS()
        self._window.show()
        self._window.activateWindow()
