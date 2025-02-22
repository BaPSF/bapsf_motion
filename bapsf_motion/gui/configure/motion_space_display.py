__all__ = ["MotionSpaceDisplay"]

import logging
import matplotlib as mpl

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout
from typing import Union

from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.motion_builder import MotionBuilder

# noqa
# the matplotlib backend imports must happen after import matplotlib and PySide6
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa


class MotionSpaceDisplay(QFrame):
    mbChanged = Signal()

    def __init__(
        self, mb: MotionBuilder = None, parent=None
    ):
        super().__init__(parent=parent)

        self._logger = logging.getLogger(f"{gui_logger.name}.MSD")

        self._mb = None
        self.link_motion_builder(mb)

        self.setStyleSheet(
            """
            MotionSpaceDisplay {
                border: 2px solid rgb(125, 125, 125);
                border-radius: 5px; 
                padding: 0px;
                margin: 0px;
            }
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.mpl_canvas = FigureCanvas()
        self.mpl_canvas.setParent(self)

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.mbChanged.connect(self.update_canvas)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mpl_canvas)

        return layout

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mb(self) -> Union[MotionBuilder, None]:
        return self._mb

    def link_motion_builder(self, mb: MotionBuilder):
        if not isinstance(mb, MotionBuilder):
            self.unlink_motion_builder()
            return

        self._mb = mb
        self.setHidden(False)

    def unlink_motion_builder(self):
        self._mb = None
        self.setHidden(True)

    def update_canvas(self):
        if not isinstance(self.mb, MotionBuilder):
            self.setHidden(True)
            return

        if self.isHidden():
            self.setHidden(False)

        self.logger.info("Redrawing plot...")
        self.logger.info(f"MB config = {self.mb.config}")

        self.mpl_canvas.figure.clear()
        ax = self.mpl_canvas.figure.gca()
        xdim, ydim = self.mb.mspace_dims
        self.mb.mask.plot(x=xdim, y=ydim, ax=ax)

        pts = self.mb.motion_list
        if pts is not None:
            ax.scatter(
                x=pts[..., 0],
                y=pts[..., 1],
                linewidth=1,
                s=2 ** 2,
                facecolors="deepskyblue",
                edgecolors="black",
            )

        self.mpl_canvas.draw()

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)
