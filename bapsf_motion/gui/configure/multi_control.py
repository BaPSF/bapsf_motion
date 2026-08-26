
from __future__ import annotations

__all__ = ["MultiControl"]

import logging
import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from typing import TYPE_CHECKING

from bapsf_motion.actors import RunManager
from bapsf_motion.gui.icons import icon_name_dict
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.widgets import DoneButton, HLinePlain, StopButton

# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta  # noqa

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent
    from bapsf_motion.gui.configure.configure_ import ConfigureGUI, RMObject


class MultiControl(QWidget):
    closing = Signal()
    returnConfig = Signal(int, object)

    def __init__(self, *, rmo: RMObject,  parent: ConfigureGUI):
        super().__init__(parent)
        self._rmo = rmo
        self._configure_gui = parent

        # Initialize Attributes
        self._logger = logging.getLogger(f"{gui_logger.name}.MC")

        # Initialize Widgets
        self.return_btn = self._init_return_btn()
        self.stop_btn = self._init_stop_btn()

        # Setup Self
        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.return_btn.clicked.connect(self.close)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._define_banner_layout())
        layout.addSpacing(8)
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(8)
        layout.addWidget(self.stop_btn)
        layout.addStretch(1)
        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.return_btn)
        layout.addStretch()
        return layout

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def rm(self) -> RunManager | None:
        return self.rmo.rm

    @property
    def rmo(self) -> RMObject:
        return self._rmo

    def _init_return_btn(self):
        btn = DoneButton("  Return", parent=self)
        font = btn.font()
        font.setPixelSize(18)
        btn.setFont(font)
        btn.setFixedHeight(36)

        # retrieve text color to define icon color
        txt_color = btn.base_style.get("color", None)
        if txt_color is not None:
            match = re.compile(
                r"rgb\(\s*"
                r"(?P<r>\d{1,3})\s*,\s*"
                r"(?P<g>\d{1,3})\s*,\s*"
                r"(?P<b>\d{1,3})\s*\)"
            ).fullmatch(txt_color)

            if match is not None:
                r = int(match.group("r"))
                g = int(match.group("g"))
                b = int(match.group("b"))
                txt_color = QColor(r, g, b)
            else:
                txt_color = None

        _icon = qta.icon(icon_name_dict["arrow-left"], color=txt_color)
        btn.setIcon(_icon)
        return btn

    def _init_stop_btn(self):
        btn = StopButton(parent=self)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(8*12)

        font = btn.font()
        font.setPixelSize(32)
        font.setBold(True)
        btn.setFont(font)

        return btn

    def closeEvent(self, event: QCloseEvent):
        self.logger.info("Closing MultiControl")

        # stop any moving motor
        rm = self.rmo.rm
        if isinstance(rm, RunManager) and rm.is_moving:
            for mg in rm.mgs.values():
                mg.stop()

            # TODO: create a dialog to display waiting for motion to stop

        self.closing.emit()
        event.accept()
