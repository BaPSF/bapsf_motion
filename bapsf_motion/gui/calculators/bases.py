"""
Collection of base classes for calculator windows and applications.
"""

__all__ = ["BaseCalculatorApp", "BaseCalculatorWindow"]

from abc import ABC, ABCMeta, abstractmethod
from pathlib import Path
from PySide6.QtCore import QPoint, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from typing import Type

from bapsf_motion.gui.widgets import StyleButton

_HERE = Path(__file__).parent
_IMAGES_PATH = (_HERE / ".." / "_images").resolve()


class QABCMainWindow(ABCMeta, type(QMainWindow)): ...


class BaseCalculatorWindow(QMainWindow, ABC, metaclass=QABCMainWindow):
    closing = Signal()
    exportParameters = Signal(object)

    _WINDOW_TITLE = NotImplemented  # type: str
    _WINDOW_MARGIN = 12
    _IMAGE_DIR = _IMAGES_PATH
    _IMAGE_NAME = NotImplemented  # type: str

    _CALCULATOR_FAMILY = None  # type: str | None
    _CALCULATOR_TYPE = None  # type: str | None

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(self._stylesheet_string)

        # set instance attributes
        self._window_margin = self._WINDOW_MARGIN
        self._image_path = self._generate_image_path()
        self._image = QPixmap(f"{self._image_path}")

        # setup window
        self.setCentralWidget(QWidget(parent=self))
        self._define_main_window()

        # initialize image widgets for background
        self._init_image_widgets()

        # define action buttons
        _btn = StyleButton("Reset to Defaults", parent=self)
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(36)
        _btn.setPointSize(14)
        p = self.geometry().topLeft() + QPoint(20, 20)
        _btn.move(p)
        self.reset_btn = _btn

        _btn = StyleButton("Export Parameters", parent=self)
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(36)
        _btn.setPointSize(14)
        p = self.geometry().topLeft() + QPoint(240, 20)
        _btn.move(p)
        self.export_btn = _btn

        # initialized widgets
        self._init_widgets()

        layout = self._define_layout()
        self.centralWidget().setLayout(layout)

        self.reset_btn.clicked.connect(self._reset_parameters)
        self.export_btn.clicked.connect(self.emit_export_parameters)
        self._connect_signals()

    @property
    def _stylesheet_string(self):
        _stylesheet = self.styleSheet()
        _stylesheet += """
            QFrame#image_frame {
                border: 2px solid rgb(125, 125, 125);
                border-radius: 5px; 
                padding: 0px;
                margin: 0px;
                background-color: white;
            }
            """
        return _stylesheet

    @abstractmethod
    def _collect_export_parameters(self) -> dict:
        return {
            "calculator_family": self._CALCULATOR_FAMILY,
            "calculator_type": self._CALCULATOR_TYPE,
        }

    @abstractmethod
    def _connect_signals(self): ...

    @abstractmethod
    @Slot()
    def _reset_parameters(self): ...

    def _define_layout(self):
        image_layout = QVBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_label)
        self.image_frame.setLayout(image_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(self.image_frame)
        layout.addStretch()
        return layout

    def _define_main_window(self):
        self.setWindowTitle(self._WINDOW_TITLE)

        # place window icon
        _image_name = "BaPSF_Logo_Color_white_background_RGB_32px.ico"
        _image_path = (_IMAGES_PATH / _image_name).resolve()
        if _image_path.exists() and _image_path.is_file():
            self.setWindowIcon(QIcon(f"{_image_path}"))

        # size window
        width = self._image.width() + 2 * self._window_margin
        height = self._image.height() + 2 * self._window_margin
        self.resize(width, height)
        self.setFixedWidth(width)
        self.setFixedHeight(height)

    def _generate_image_path(self):
        if not isinstance(self._IMAGE_DIR, Path):
            raise TypeError(
                f"Class attribute is invalid, got type "
                f"{type(self._IMAGE_DIR)} but expected a "
                f"pathlib.Path instance."
            )
        if not self._IMAGE_DIR.exists():
            raise ValueError(f"The image directory '{self._IMAGE_DIR}' does NOT exist.")
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
            raise ValueError(f"The image '{_image_path}' does NOT exist.")
        if not _image_path.is_file():
            raise ValueError(f"The image '{_image_path}' does NOT a file.")
        return _image_path

    def _init_image_widgets(self):
        self.image_label = QLabel(parent=self)
        self.image_label.setPixmap(self._image)

        self.image_frame = QFrame(parent=self)
        self.image_frame.setObjectName("image_frame")
        self.image_frame.setFixedWidth(self.width() - 2 * self._window_margin)
        self.image_frame.setFixedHeight(self.height() - 2 * self._window_margin)

    @abstractmethod
    def _init_widgets(self): ...

    @Slot()
    def emit_export_parameters(self):
        parameters = self._collect_export_parameters()
        self.exportParameters.emit(parameters)

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

    @property
    def calculator(self) -> BaseCalculatorWindow:
        return self._window
