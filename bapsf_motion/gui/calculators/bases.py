__all__ = ["BaseCalculatorApp", "BaseCalculatorWindow"]
from abc import ABC, abstractmethod
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from typing import Type

_HERE = Path(__file__).parent
_IMAGES_PATH = (_HERE / ".." / "_images").resolve()


class BaseCalculatorWindow(QMainWindow, ABC):
    closing = Signal()

    _WINDOW_TITLE = NotImplemented  # type: str
    _WINDOW_MARGIN = 12
    _IMAGE_DIR = _IMAGES_PATH
    _IMAGE_NAME = NotImplemented  # type: str

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setCentralWidget(QWidget(parent=self))

        self._image_path = self._generate_image_path()
        pixmap = QPixmap(f"{self._image_path}")
        self._image = pixmap

        self._window_margin = self._WINDOW_MARGIN
        self._define_main_window()

    @abstractmethod
    def _connect_signals(self):
        ...

    def _generate_image_path(self):
        if not isinstance(self._IMAGE_DIR, Path):
            raise TypeError(
                f"Class attribute is invalid, got type "
                f"{type(self._IMAGE_DIR)} but expected a "
                f"pathlib.Path instance."
            )
        if not self._IMAGE_DIR.exists():
            raise ValueError(
                f"The image directory '{self._IMAGE_DIR}' does NOT exist."
            )
        if not self._IMAGE_DIR.is_dir():
            raise ValueError(
                f"The image directory '{self._IMAGE_DIR}' does NOT a directory."
            )
        if not isinstance(self._IMAGE_NAME, str):
            raise TypeError(
                f"Class attribute is invalid, got type "
                f"{type(self._IMAGE_NAME)} but expected a string."
            )
        _image_path = (self._IMAGE_DIR / self._IMAGE_NAME).resolve()
        if not _image_path.exists():
            raise ValueError(
                f"The image '{_image_path}' does NOT exist."
            )
        if not _image_path.is_file():
            raise ValueError(
                f"The image '{_image_path}' does NOT a file."
            )
        return _image_path

    def _define_main_window(self):
        self.setWindowTitle(self._WINDOW_TITLE)
        width = self._image.width() + 2 * self._window_margin
        height = self._image.height() + 2 * self._window_margin
        self.resize(width, height)
        self.setFixedWidth(width)
        self.setFixedHeight(height)

    def closeEvent(self, event: QCloseEvent):
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
