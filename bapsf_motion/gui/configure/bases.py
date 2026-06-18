"""
Module contains base classes for various
`~PySide6.QtWidgets.QWidget`\'s used in the Configuration GUI.
"""

__all__ = [
    "_ABCMetaQWidget",
    "_ConfigOverlay",
    "_OverlayWidget",
]

import logging

from abc import ABC, ABCMeta, abstractmethod
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget
from typing import Any, Dict, Union

from bapsf_motion.actors import MotionGroup
from bapsf_motion.gui.configure import motion_group_widget as mgw
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.configure.message_boxes import WarningMessageBox
from bapsf_motion.gui.widgets import DiscardButton, DoneButton


class _ABCMetaQWidget(ABCMeta, type(QWidget)): ...  # noqa: E701


class _OverlayWidget(QWidget):
    closing = Signal()

    def __init__(self, parent: QWidget | None):
        super().__init__(parent=parent)

        # make the window frameless
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.background_fill_color = QColor(30, 30, 30, 100)
        self.background_pen_color = QColor(30, 30, 30, 200)

        _palette = self.style().standardPalette()
        self.overlay_fill_color = _palette.color(_palette.ColorRole.Window)

        self.overlay_pen = QPen(QColor(60, 60, 60))
        self.overlay_pen.setWidth(3)

        self._margins = [0.01, 0.01]  # [ w_margin / width, h_margin / height]
        self._set_contents_margins(*self._margins)

    def _set_contents_margins(self, width_fraction, height_fraction):
        width = int(width_fraction * self.parent().width())
        height = int(height_fraction * self.parent().height())

        self.setContentsMargins(width, height, width, height)

    def paintEvent(self, event):
        # This method is, in practice, drawing the contents of
        # your window.

        # get current window size
        s = self.parent().size()
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        qp.setPen(self.background_pen_color)
        qp.setBrush(self.background_fill_color)
        qp.drawRoundedRect(0, 0, s.width(), s.height(), 3, 3)

        # draw overlay
        _pen = QPen(self.overlay_pen)
        _pen.setWidth(3)
        qp.setPen(_pen)
        qp.setBrush(self.overlay_fill_color)

        self.contentsRect().width()
        ow = int((s.width() - self.contentsRect().width()) / 2)
        oh = int((s.height() - self.contentsRect().height()) / 2)
        qp.drawRoundedRect(
            ow,
            oh,
            self.contentsRect().width(),
            self.contentsRect().height(),
            5,
            5,
        )

        qp.end()

    def closeEvent(self, event):
        self.closing.emit()
        event.accept()


class _ConfigOverlay(_OverlayWidget, ABC, metaclass=_ABCMetaQWidget):
    configChanged = Signal()
    returnConfig = Signal(object)

    def __init__(self, mg: Union[MotionGroup, None], parent: "mgw.MGWidget | None" = None):
        super().__init__(parent=parent)

        self._logger = gui_logger
        self._mg = mg

        # Define BUTTONS

        _btn = DoneButton("Add / Update", parent=self)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = DiscardButton(parent=self)
        self.discard_btn = _btn

    def _connect_signals(self):
        self.discard_btn.clicked.connect(self.discard_close)
        self.done_btn.clicked.connect(self.return_and_close)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        """Working motion group."""
        return self._mg

    @Slot()
    def discard_close(self):
        if not self.done_btn.isEnabled():
            # no changes have been made, just discard
            self._safe_return_config_emit({})
            self.close()
            return

        dialog = WarningMessageBox(
            message=(
                f"Quitting now will discard any changes.  If you want to "
                f"keep changes, then use the 'DONE' button."
            ),
            button_layout="approve",
            parent=self,
        )
        proceed = bool(dialog.exec())
        if not proceed:
            return

        self._safe_return_config_emit({})
        self.close()

    @abstractmethod
    @Slot()
    def return_and_close(self): ...

    def _safe_return_config_emit(self, config: Dict[str, Any]):
        self.returnConfig.emit(config)

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)
