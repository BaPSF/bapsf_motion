__all__ = ["MotionSpaceDisplay"]

import logging
import numpy as np
import warnings

from PySide6.QtCore import Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout
from typing import Union

from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.motion_builder import MotionBuilder

# noqa
# the matplotlib backend imports must happen after import matplotlib and PySide6
import matplotlib as mpl
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib import pyplot as plt
from matplotlib.collections import PathCollection
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
        self.targetPositionSelected.connect(self.update_target_position_plot)

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

    def _get_plot_axis_by_name(self, name: str):
        fig_axes = self.mpl_canvas.figure.axes
        for ax in fig_axes:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                legend_handles, legend_labels = ax.get_legend_handles_labels()

            if name not in legend_labels:
                continue

            index = legend_labels.index(name)
            handler = legend_handles[index]

            return ax, handler

        return None

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

        # retrieve last position
        stuff = self._get_plot_axis_by_name("position")
        if stuff is not None:
            ax, handler = stuff  # type: plt.Axes, PathCollection
            position = handler.get_offsets()
        else:
            position = None

        # retrieve last target position
        stuff = self._get_plot_axis_by_name("target")
        if stuff is not None:
            ax, handler = stuff  # type: plt.Axes, PathCollection
            target_position = handler.get_offsets()
        else:
            target_position = None

        fig = self.mpl_canvas.figure
        fig.clear()
        ax = fig.gca()

        xdim, ydim = self.mb.mspace_dims
        self.mb.mask.plot(x=xdim, y=ydim, ax=ax, add_colorbar=False, label="mask")

        fig.tight_layout()

        # Draw motion list
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

        # Draw insertion point
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

        # Draw target position
        self.update_target_position_plot(position=target_position)

        # Draw current position
        self.update_position_plot(position=position)

        self.mpl_canvas.draw()

    def update_target_position_plot(self, position):
        self.logger.info(f"Drawing target position {position}")

        if isinstance(position, np.ndarray):
            position = position.squeeze()
            position = position.tolist()

        if not bool(position):
            position = None

        # add target position dot
        _label = "target"
        stuff = self._get_plot_axis_by_name(_label)
        if stuff is not None:
            ax, handler = stuff  # type: plt.Axes, PathCollection

            if position is None:
                handler.remove()
            else:
                handler.set_offsets(position)
        elif position is None:
            pass
        else:
            ax = self.mpl_canvas.figure.gca()

            ax.scatter(
                x=position[0],
                y=position[1],
                s=7 ** 2,
                linewidth=2,
                facecolors="none",
                edgecolors="blue",
                label=_label,
            )

        self.mpl_canvas.draw()

    def update_position_plot(self, position):
        self.logger.debug(f"Drawing target position {position}")

        if isinstance(position, np.ndarray):
            position = position.squeeze()
            position = position.tolist()

        if not bool(position):
            position = None

        # add position dot
        _label = "position"
        stuff = self._get_plot_axis_by_name(_label)
        if stuff is not None:
            ax, handler = stuff  # type: plt.Axes, PathCollection

            if position is None:
                handler.remove()
            else:
                handler.set_offsets(position)
        elif position is None:
            return
        else:
            ax = self.mpl_canvas.figure.gca()

            ax.scatter(
                x=position[0],
                y=position[1],
                s=7 ** 2,
                linewidth=2,
                facecolors="none",
                edgecolors="black",
                label=_label,
            )

        # add probe shaft (line from insertion to position
        _label = "probe"
        stuff = self._get_plot_axis_by_name(_label)
        insertion_point = self.mb.get_insertion_point()
        if (insertion_point is None or position is None) and stuff is not None:
            # not enough to update plot, so remove EXISTING plot
            ax, handler = stuff
            handler.remove()
        elif insertion_point is None or position is None:
            # nothing to plot and plot does NOT already exist
            pass
        elif stuff is not None:
            # update existing plot
            ax, handler = stuff  # type: plt.Axes, plt.Line2D

            xdata = [insertion_point[0], position[0]]
            ydata = [insertion_point[1], position[1]]

            handler.set_xdata(xdata)
            handler.set_ydata(ydata)
        else:
            # plot does NOT exist, make plot
            ax = self.mpl_canvas.figure.gca()

            xdata = [insertion_point[0], position[0]]
            ydata = [insertion_point[1], position[1]]

            ax.plot(
                xdata,
                ydata,
                color="black",
                linewidth=2,
                label=_label,
            )

        self.mpl_canvas.draw()

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)
