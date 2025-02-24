__all__ = ["MotionSpaceDisplay"]

import logging
import matplotlib as mpl

from matplotlib.collections import PathCollection
from PySide6.QtCore import Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout
from typing import Union

from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.motion_builder import MotionBuilder

# noqa
# the matplotlib backend imports must happen after import matplotlib and PySide6
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib.backend_bases import Event, MouseEvent, PickEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar  # noqa


class MotionSpaceDisplay(QFrame):
    mbChanged = Signal()
    targetPositionSelected = Signal(list)

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

        self.mpl_toolbar = NavigationToolbar(self.mpl_canvas, parent=self)

        self.setLayout(self._define_layout())

        self._mpl_pick_callback_id = None
        self._connect_signals()

    def _connect_signals(self):
        self.mbChanged.connect(self.update_canvas)
        self._mpl_pick_callback_id = self.mpl_canvas.mpl_connect(
            "pick_event", self.on_pick  # noqa
        )

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mpl_toolbar)
        layout.addWidget(self.mpl_canvas)

        return layout

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mb(self) -> Union[MotionBuilder, None]:
        return self._mb

    def on_pick(self, event: PickEvent):
        gui_event = event.guiEvent  # type: QMouseEvent

        artist = event.artist  # noqa
        if not isinstance(artist, PathCollection):
            self.logger.warning(
                f"Currently only know how to retrieve data from a "
                f"PathCollection artist (i.e. an artist created with "
                f"pyplot.scatter()), received artist type {type(artist)}."
            )
            return

        # A PickEvent associated with a PathCollection artist will have
        # the attribute ind.  ind is a list of ints corresponding to the
        # indices of the data used to create the scatter plot
        if len(event.ind) != 1:
            self.logger.info(
                f"Could not select data point, too many point close to "
                f"the mouse click."
            )
            return
        index = event.ind[0]  # noqa

        # get the date from the artist
        data = artist.get_offsets()
        target_position = data[index, :]

        self.logger.info(f"target position = {target_position}")
        self.targetPositionSelected.emit(target_position)

    def link_motion_builder(self, mb: Union[MotionBuilder, None]):
        self.logger.info(f"Linking Motion Builder {mb}")

        self.blockSignals(True)
        self.unlink_motion_builder()
        self.blockSignals(False)

        if not isinstance(mb, MotionBuilder):
            self.mbChanged.emit()
            return

        self._mb = mb
        self.setHidden(False)
        self.mbChanged.emit()

    def unlink_motion_builder(self):
        self._mb = None
        self.setHidden(True)
        self.mbChanged.emit()

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
        self.mb.mask.plot(x=xdim, y=ydim, ax=ax, label="mask")

        pts = self.mb.motion_list
        if pts is not None:
            ax.scatter(
                x=pts[..., 0],
                y=pts[..., 1],
                linewidth=1,
                s=3 ** 2,
                facecolors="deepskyblue",
                edgecolors="black",
                picker=True,
                label="motion_list",
            )

        insertion_point = self.mb.get_insertion_point()
        if insertion_point is not None:
            ax.scatter(
                x=insertion_point[0],
                y=insertion_point[1],
                s=3 ** 2,
                linewidth=2,
                facecolors="none",
                edgecolors="red",
                label="insertion_point",
            )

            # reset x range of plot
            xlim = ax.get_xlim()
            if insertion_point[0] > xlim[1]:
                xlim = [xlim[0], 1.05 * insertion_point[0]]
            elif insertion_point[0] < xlim[0]:
                xlim = [1.05 * insertion_point[0], xlim[1]]
            ax.set_xlim(xlim)

            # reset y range of plot
            ylim = ax.get_ylim()
            if insertion_point[1] > ylim[1]:
                ylim = [ylim[0], 1.05 * insertion_point[1]]
            elif insertion_point[1] < ylim[0]:
                ylim = [1.05 * insertion_point[1], ylim[1]]
            ax.set_ylim(ylim)

        self.mpl_canvas.draw()

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)
