"""
Module contains the `~PySide6.QtWidgets.QWidget` used for displaying /
plotting the :term:`motion space` associated with a |MotionBuilder|
instance.
"""

__all__ = ["MotionSpaceDisplay"]

import logging
import matplotlib as mpl
import numpy as np
import warnings

from abc import ABC, ABCMeta, abstractmethod
from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QWidget
from typing import Dict, List, TYPE_CHECKING

from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.motion_builder import MotionBuilder

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

# the matplotlib backend imports must happen after import matplotlib and PySide6
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib import pyplot as plt  # noqa
from matplotlib.backend_bases import DrawEvent, PickEvent  # noqa
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa
from matplotlib.backends.backend_qtagg import (  # noqa
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.collections import PathCollection  # noqa


class _ABCMotionSpaceDisplay(ABCMeta, type(QWidget)): ...


class _RedrawDisplaySignals(QObject):
    All = Signal()
    MotionList = Signal()
    Position = Signal(list)
    TargetPosition = Signal(list)


class _AnimationSignals(QObject):
    Cleared = Signal()
    Finished = Signal()
    Paused = Signal()
    Started = Signal()

    Clear = Signal()
    Pause = Signal()
    Start = Signal()
    Stop = Signal()


class _MSDBase(QWidget, ABC, metaclass=_ABCMotionSpaceDisplay):
    mbChanged = Signal()
    targetPositionSelected = Signal(list)
    animateMotionList = _AnimationSignals()
    redrawSignals = _RedrawDisplaySignals()

    _default_logger_name = "MSD-Base"
    _default_legend_names = [
        "motion_list",
        "probe",
        "position",
        "target",
        "insertion_point",
    ]

    def __init__(
        self,
        logger: logging.Logger,
        mb: MotionBuilder | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        self._logger = self._init_logger(logger)
        self._mb = self._init_motion_builder(mb)

        # Initialize plotting control attributes
        #
        # _display_position : bool
        #     If True, plot the current position of the probe drive.
        # _display_target_position : bool
        #     If True, plot the target position.
        # _display_probe : bool
        #     If True, add to the plot a representation of the probe [shaft]
        # _animate_payload : dict
        #     A dictionary payload when animating the motion list.
        #      "finished"   - bool   - has the animation finsihed
        #      "timer"      - QTimer - timer instance
        #      "delay"      - int    - timer interval
        #      "index"      - int    - next motionlist index to animate to
        #      "index_step" - int    - delta / step between animated index
        # _motionlist_plot_names : list[str]
        #     list of motionlist names ... these are the same as the
        #     MotionBuilder layer names
        # _draw_all : True
        #     If True, then (re)draw everything.  If False, then only redraw
        #     the artists that are marked animated=True.  (Note this is
        #     matplotlib's animated, and not our motion list animateion.)
        # _cid_on_draw :
        #     matplotlib call back ID for the "draw_event"
        # _mpl_pick_callback_id :
        #     matplotlib call back ID for the "pick_event"
        #
        self._display_position = True
        self._display_target_position = True
        self._display_probe = True
        self._animate_payload = None
        self._motionlist_plot_names = None  # type: List[str] | None
        self._draw_all = True
        self._cid_on_draw = None
        self._mpl_pick_callback_id = None

    def _connect_redraw_signals(self):
        self.redrawSignals.All.connect(self.redraw_display)
        self.redrawSignals.MotionList.connect(self.redraw_motion_list_plot)
        self.redrawSignals.Position.connect(self.redraw_position_plot)
        self.redrawSignals.TargetPosition.connect(self.redraw_target_position_plot)

    def _connect_animate_motion_list_signals(self):
        self.animateMotionList.Clear.connect(self.animate_motion_list_clear)
        self.animateMotionList.Pause.connect(self.animate_motion_list_pause)
        self.animateMotionList.Start.connect(self.animate_motion_list_start)
        self.animateMotionList.Stop.connect(self.animate_motion_list_stop)

        self.animateMotionList.Finished.connect(self.animate_motion_list_stop)

    @abstractmethod
    def link_motion_builder(self, mb: MotionBuilder | None): ...

    @abstractmethod
    def unlink_motion_builder(self): ...

    @abstractmethod
    @Slot()
    def animate_motion_list_clear(self): ...

    @abstractmethod
    @Slot()
    def animate_motion_list_pause(self): ...

    @abstractmethod
    @Slot()
    def animate_motion_list_start(self): ...

    @abstractmethod
    @Slot()
    def animate_motion_list_stop(self): ...

    @abstractmethod
    @Slot()
    def redraw_display(self): ...

    @abstractmethod
    @Slot()
    def redraw_motion_list_plot(self): ...

    @abstractmethod
    @Slot(list)
    def redraw_target_position_plot(self, position): ...

    @abstractmethod
    @Slot(list)
    def redraw_position_plot(self, position): ...

    def _init_logger(self, logger: logging.Logger) -> logging.Logger:
        if not isinstance(logger, logging.Logger):
            logger = logging.getLogger(f"{gui_logger.name}.{self._default_logger_name}")
        else:
            logger = logging.getLogger(f"{logger.name}.{self._default_logger_name}")

        return logger

    @staticmethod
    def _init_motion_builder(mb: MotionBuilder | None) -> MotionBuilder | None:
        if mb is not None and not isinstance(mb, MotionBuilder):
            raise TypeError(
                "Argument 'mb' must be None or an instance of MotionBuilder, "
                f"got type {type(mb)} instead."
            )

        return mb

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mb(self) -> MotionBuilder | None:
        return self._mb

    @property
    def display_position(self) -> bool:
        return self._display_position

    @display_position.setter
    def display_position(self, value: bool):
        if not isinstance(value, bool):
            return

        self._display_position = value
        if not value:
            self._display_probe = value

    @property
    def display_target_position(self) -> bool:
        return self._display_target_position

    @display_target_position.setter
    def display_target_position(self, value: bool):
        if not isinstance(value, bool):
            return

        self._display_target_position = value

    @property
    def display_probe(self) -> bool:
        return self._display_probe

    @display_probe.setter
    def display_probe(self, value: bool):
        if not isinstance(value, bool):
            return

        self._display_probe = value
        if value:
            self._display_position = value

    @property
    def is_animating_motion_list(self):
        if self._animate_payload is None:
            return False

        if self._animate_payload["finished"]:
            return False

        _timer = self._animate_payload["timer"]  # type: QTimer
        return _timer.isActive()

    def closeEvent(self, event: "QCloseEvent"):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)


class MotionSpaceDisplay2D(_MSDBase):
    dimensionality = 2
    _default_logger_name = "MSD-2D"

    def __init__(
        self,
        logger: logging.Logger,
        mb: MotionBuilder | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(logger=logger, mb=mb, parent=parent)

        # Define WIDGETS
        self.mpl_canvas = self._init_mpl_canvas()
        self.mpl_toolbar = self._init_mpl_toolbar()

        self.setLayout(self._define_layout())
        self._connect_signals()

        self.mbChanged.emit()

    def _connect_signals(self):
        self._connect_animate_motion_list_signals()
        self._connect_redraw_signals()

        self.mbChanged.connect(self.redraw_display)
        self.targetPositionSelected.connect(self.redraw_target_position_plot)

        # matplotlib events
        self._mpl_pick_callback_id = self.mpl_canvas.mpl_connect(
            "pick_event", self.on_pick  # noqa
        )
        self._cid_on_draw = self.mpl_canvas.mpl_connect(
            "draw_event", self.on_draw
        )  # noqa

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mpl_toolbar)
        layout.addWidget(self.mpl_canvas)

        return layout

    def _init_mpl_canvas(self):
        canvas = FigureCanvas()
        canvas.setParent(self)
        return canvas

    def _init_mpl_toolbar(self):
        toolbar = NavigationToolbar(self.mpl_canvas, parent=self)
        return toolbar

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

    def _animate_motion_list_init_payload(self):
        delay = 200  # msec
        _timer = QTimer(parent=self)
        _timer.setInterval(delay)
        _timer.timeout.connect(self._update_motion_list_trace)

        motionlist_size = self.mb.motion_list.shape[0]
        index_step = np.floor(motionlist_size / (60000 / _timer.interval())).astype(int)
        index_step = 1 if index_step == 0 else index_step

        self._animate_payload = {
            "index": 0,  # type: int
            "index_step": index_step,  # type: int
            "delay": delay,  # type: int
            "timer": _timer,  # type: QTimer
            "finished": False,
        }

    @Slot()
    def animate_motion_list_clear(self):
        if self._animate_payload is None:
            return

        self._animate_payload["timer"].stop()
        self._animate_payload["timer"].deleteLater()
        self._animate_payload = None

        _animate_ml_labels = ["motionlist_start", "motionlist_stop", "motionlist_trace"]
        for _label in _animate_ml_labels:
            stuff = self._get_plot_axis_by_name(_label)
            if stuff is None:
                continue

            ax, handler = stuff
            handler.remove()

        self.mpl_canvas.draw()

        self.animateMotionList.Cleared.emit()

    @Slot()
    def animate_motion_list_pause(self):
        if self._animate_payload is None:
            return

        self._animate_payload["timer"].stop()

        if not self._animate_payload["finished"]:
            self.animateMotionList.Paused.emit()

    @Slot()
    def animate_motion_list_start(self):
        if self._animate_payload is not None and not self._animate_payload["finished"]:
            self._animate_payload["timer"].start()
            self.animateMotionList.Started.emit()
            return
        elif self._animate_payload is not None:
            self.animate_motion_list_clear()
            self._animate_payload = None
        elif self.mb.motion_list is None:
            self.animate_motion_list_clear()
            return

        self._animate_motion_list_init_payload()
        self._animate_payload["timer"].start()  # noqa

        self.animateMotionList.Started.emit()

    @Slot()
    def animate_motion_list_stop(self):
        self.animate_motion_list_pause()

    @Slot()
    def _update_motion_list_trace(self, *, to_index: int | None = None):
        if to_index is None and self._animate_payload is None:
            return
        elif to_index is None:
            to_index = self._animate_payload["index"]
        elif self._animate_payload is None:
            return
        elif self._animate_payload["finished"]:
            return

        # update plot
        _animate_ml_labels = ["motionlist_start", "motionlist_stop", "motionlist_trace"]
        for _label in _animate_ml_labels:

            stuff = self._get_plot_axis_by_name(_label)

            if stuff is not None and _label in ("motionlist_start", "motionlist_stop"):
                ax, handler = stuff  # type: plt.Axes, PathCollection

                index = 0 if _label == "motionlist_start" else to_index
                point = self.mb.motion_list[index, ...].squeeze()

                handler.set_offsets(point)
            elif stuff is not None:
                # this is the trace
                ax, handler = stuff  # type: plt.Axes, plt.Line2D

                xdata = self.mb.motion_list[0 : to_index + 1, 0]
                ydata = self.mb.motion_list[0 : to_index + 1, 1]

                handler.set_xdata(xdata)
                handler.set_ydata(ydata)
            elif _label == "motionlist_trace":
                # trace has not been made yet
                ax = self.mpl_canvas.figure.gca()

                xdata = self.mb.motion_list[0 : to_index + 1, 0]
                ydata = self.mb.motion_list[0 : to_index + 1, 1]

                ax.plot(
                    xdata,
                    ydata,
                    color="black",
                    linewidth=1,
                    label=_label,
                    animated=True,
                )
            else:
                # this is the start and end points
                ax = self.mpl_canvas.figure.gca()

                points = self.mb.motion_list[0 : to_index + 1, ...]

                ax.scatter(
                    x=points[..., 0],
                    y=points[..., 1],
                    s=6**2,
                    linewidth=1,
                    facecolors="none",
                    edgecolors="black",
                    label=_label,
                    animated=True,
                )

        self.mpl_canvas.draw()
        if to_index == self.mb.motion_list.shape[0] - 1:
            self._animate_payload["finished"] = True
            self.animateMotionList.Finished.emit()
            return

        to_index += self._animate_payload["index_step"]
        if to_index >= self.mb.motion_list.shape[0]:
            to_index = self.mb.motion_list.shape[0] - 1

        self._animate_payload["index"] = to_index

    def on_draw(self, event: DrawEvent):
        if self._draw_all:
            self.mpl_canvas.mpl_disconnect(self._cid_on_draw)
            self.mpl_canvas.draw()
            self._cid_on_draw = self.mpl_canvas.mpl_connect("draw_event", self.on_draw)
            self._draw_all = False
        else:
            fig = self.mpl_canvas.figure
            fig_axes = fig.axes  # type: List[plt.Axes]
            for ax in fig_axes:
                artists = ax.get_children()
                for artist in artists:
                    if not artist.get_animated():
                        continue

                    fig.draw_artist(artist)

            self.mpl_canvas.blit(fig.bbox)

    def on_pick(self, event: PickEvent):
        if not self.display_target_position:
            return

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

    def link_motion_builder(self, mb: MotionBuilder | None):
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

    @Slot()
    def redraw_display(self):
        if not isinstance(self.mb, MotionBuilder):
            self.setHidden(True)
            return

        if self.isHidden():
            self.setHidden(False)

        self.logger.info("Redrawing Motion Space Display...")

        # stop motion list animation while re-plotting
        is_animating = self.is_animating_motion_list
        self.blockSignals(True)
        self.animate_motion_list_clear()
        self.blockSignals(False)

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

        self._draw_all = True
        fig = self.mpl_canvas.figure
        fig.clear()
        ax = fig.gca()

        xdim, ydim = self.mb.mspace_dims
        self.mb.mask.plot(x=xdim, y=ydim, ax=ax, add_colorbar=False, label="mask")

        fig.tight_layout()

        # Draw motion list
        self.redraw_motion_list_plot()

        # Draw insertion point
        insertion_point = self.mb.get_insertion_point()
        if insertion_point is not None:
            ax.scatter(
                x=insertion_point[0],
                y=insertion_point[1],
                s=3**2,
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
        if self.display_target_position:
            self.redraw_target_position_plot(position=target_position)

        # Draw current position
        if self.display_position:
            self.redraw_position_plot(position=position)

        # Draw legend
        self.redraw_legend()

        self.mpl_canvas.draw()

        # re-start the motion list animation
        if is_animating:
            self.blockSignals(True)
            self.animate_motion_list_start()
            self.blockSignals(False)

        self.logger.info("Re-draw DONE.")

    def redraw_legend(self):
        _plotted_layers = (
            [] if self._motionlist_plot_names is None else self._motionlist_plot_names
        )
        _names = set(self._default_legend_names + _plotted_layers)

        # gather handles for legend
        handles = []
        for name in _names:
            stuff = self._get_plot_axis_by_name(name)
            if stuff is None:
                continue

            ax, handle = stuff
            handles.append(handle)

        if len(handles) == 0:
            self.mpl_canvas.draw()
            return

        ax = self.mpl_canvas.figure.gca()
        ax.legend(handles=handles)

        self.mpl_canvas.draw()

    @Slot()
    def redraw_motion_list_plot(self):
        self.animate_motion_list_clear()

        # plot the individual point layers (if join scheme is sequential)
        _layer_names = [layer.name for layer in self.mb.layers]
        _plotted_layer_names = set(
            [] if self._motionlist_plot_names is None else self._motionlist_plot_names
        )
        _labels = _layer_names + list(_plotted_layer_names - set(_layer_names))
        _plotted_layer_names = []
        edgecolor = "none"
        facecolors = [
            "deepskyblue",
            "orangered",
            "slategrey",
            "teal",
            "darkorange",
            "darkviolet",
            "deeppink",
        ]
        color_index = 0
        for _label in _labels:
            stuff = self._get_plot_axis_by_name(_label)
            if stuff is not None:
                ax, handler = stuff  # type: plt.Axes, PathCollection

                if (
                    _label not in _layer_names
                    or self.mb.layer_to_motionlist_scheme == "merge"
                    or len(self.mb.layers) == 1
                ):
                    handler.remove()
                else:
                    data = self.mb._ds[_label].data
                    pts = self.mb.flatten_points(data)
                    mask = self.mb.generate_excluded_mask(pts)
                    pts = pts[mask, ...]

                    handler.set_offsets(pts)
                    handler.set_facecolor(facecolors[color_index])
                    handler.set_edgecolor(edgecolor)

                    color_index += 1
                    _plotted_layer_names.append(_label)
            elif (
                _label not in _layer_names
                or self.mb.layer_to_motionlist_scheme == "merge"
                or len(self.mb.layers) == 1
            ):
                pass
            else:
                ax = self.mpl_canvas.figure.gca()

                data = self.mb._ds[_label].data
                pts = self.mb.flatten_points(data)
                mask = self.mb.generate_excluded_mask(pts)
                pts = pts[mask, ...]

                ax.scatter(
                    x=pts[..., 0],
                    y=pts[..., 1],
                    s=4**2,
                    facecolors=facecolors[color_index],
                    edgecolors=edgecolor,
                    label=_label,
                    animated=True,
                )

                color_index += 1
                _plotted_layer_names.append(_label)

            color_index = color_index % len(facecolors)
        self._motionlist_plot_names = _plotted_layer_names

        # add motion list "base" plot
        _label = "motion_list"
        motion_list = self.mb.motion_list
        facecolors = (
            "none"
            if (
                motion_list is None
                or (
                    len(self.mb.layers) > 1
                    and self.mb.layer_to_motionlist_scheme == "sequential"
                )
            )
            else "deepskyblue"
        )
        stuff = self._get_plot_axis_by_name(_label)
        if stuff is not None:
            ax, handler = stuff  # type: plt.Axes, PathCollection

            if motion_list is None:
                handler.remove()
            else:
                handler.set_offsets(motion_list)
                handler.set_facecolor(facecolors)
        elif motion_list is None:
            pass
        else:
            ax = self.mpl_canvas.figure.gca()

            ax.scatter(
                x=motion_list[..., 0],
                y=motion_list[..., 1],
                s=4**2,
                linewidth=1,
                facecolors=facecolors,
                edgecolors="black",
                picker=True,
                label=_label,
                animated=True,
            )

        self.redraw_legend()
        self.mpl_canvas.draw()

    @Slot(list)
    def redraw_target_position_plot(self, position):
        self.logger.info(f"Drawing target position {position}")

        if not self.display_target_position:
            position = None
        elif isinstance(position, np.ndarray):
            position = position.squeeze()
            position = position.tolist()

        if not isinstance(position, list) or len(position) == 0:
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
            # The plot was never made and there is no position to update
            return
        else:
            ax = self.mpl_canvas.figure.gca()

            ax.scatter(
                x=position[0],
                y=position[1],
                s=7**2,
                linewidth=2,
                facecolors="none",
                edgecolors="blue",
                label=_label,
                animated=True,
            )

        self.redraw_legend()
        self.mpl_canvas.draw()

    @Slot(list)
    def redraw_position_plot(self, position):
        self.logger.info(f"Drawing position {position}")

        if not self.display_position:
            position = None
        elif isinstance(position, np.ndarray):
            position = position.squeeze()
            position = position.tolist()

        if not isinstance(position, list) or len(position) == 0:
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
            # The plot was never made and there is no position to update
            return
        else:
            ax = self.mpl_canvas.figure.gca()

            ax.scatter(
                x=position[0],
                y=position[1],
                s=7**2,
                linewidth=2,
                facecolors="none",
                edgecolors="black",
                label=_label,
                animated=True,
            )

        # add probe shaft (line from insertion to position
        _label = "probe"
        stuff = self._get_plot_axis_by_name(_label)
        insertion_point = (
            None
            if not isinstance(self.mb, MotionBuilder)
            else self.mb.get_insertion_point()
        )
        if (
            insertion_point is None or position is None or not self.display_probe
        ) and stuff is not None:
            # not enough to update plot, so remove EXISTING plot
            ax, handler = stuff
            handler.remove()
        elif insertion_point is None or position is None or not self.display_probe:
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
                animated=True,
            )

        self.redraw_legend()
        self.mpl_canvas.draw()


class MotionSpaceDisplay(QFrame):
    targetPositionSelected = Signal(list)

    animateMotionList = _AnimationSignals()
    redrawSignals = _RedrawDisplaySignals()

    _default_legend_names = [
        "motion_list",
        "probe",
        "position",
        "target",
        "insertion_point",
    ]

    def __init__(self, mb: MotionBuilder | None = None, parent: QWidget | None = None):
        super().__init__(parent=parent)

        self._logger = logging.getLogger(f"{gui_logger.name}.MSD")
        self._mb = self._init_motion_builder(mb)

        # Initialize display attributes
        self._display_visibility = {
            "position": False,
            "target_position": False,
            "probe": False,
            # "insertion_point": False,
        }  # type: Dict[str, bool]

        # Define WIDGETS
        self.display = self._init_display()

        self._init_self()
        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self._connect_display_signals()

    def _connect_display_signals(self):
        if not isinstance(self.display, _MSDBase):
            return

        # animation response signals
        self.display.animateMotionList.Cleared.connect(
            self.animateMotionList.Cleared.emit
        )
        self.display.animateMotionList.Finished.connect(
            self.animateMotionList.Finished.emit
        )
        self.display.animateMotionList.Paused.connect(self.animateMotionList.Paused.emit)
        self.display.animateMotionList.Started.connect(
            self.animateMotionList.Started.emit
        )

        # annimation action signals
        self.animateMotionList.Clear.connect(self.display.animateMotionList.Clear.emit)
        self.animateMotionList.Pause.connect(self.display.animateMotionList.Pause.emit)
        self.animateMotionList.Start.connect(self.display.animateMotionList.Start.emit)

        self.display.targetPositionSelected.connect(self.targetPositionSelected.emit)

        # signals to trigger a redraw
        self.redrawSignals.All.connect(self.display.redrawSignals.All.emit)
        self.redrawSignals.MotionList.connect(self.display.redrawSignals.MotionList.emit)
        self.redrawSignals.Position.connect(self.display.redrawSignals.Position.emit)
        self.redrawSignals.TargetPosition.connect(
            self.display.redrawSignals.TargetPosition.emit
        )

    def _disconnect_display_signals(self):
        if not isinstance(self.display, _MSDBase):
            return

        self.display.animateMotionList.Cleared.disconnect(
            self.animateMotionList.Cleared.emit
        )
        self.display.animateMotionList.Finished.disconnect(
            self.animateMotionList.Finished.emit
        )
        self.display.animateMotionList.Paused.disconnect(
            self.animateMotionList.Paused.emit
        )
        self.display.animateMotionList.Started.disconnect(
            self.animateMotionList.Started.emit
        )

        self.display.targetPositionSelected.disconnect(self.targetPositionSelected.emit)

        self.animateMotionList.Clear.disconnect(self.display.animateMotionList.Clear.emit)
        self.animateMotionList.Pause.disconnect(self.display.animateMotionList.Pause.emit)
        self.animateMotionList.Start.disconnect(self.display.animateMotionList.Start.emit)

        self.redrawSignals.All.disconnect(self.display.redrawSignals.All.emit)
        self.redrawSignals.MotionList.disconnect(
            self.display.redrawSignals.MotionList.emit
        )
        self.redrawSignals.Position.disconnect(self.display.redrawSignals.Position.emit)
        self.redrawSignals.TargetPosition.disconnect(
            self.display.redrawSignals.TargetPosition.emit
        )

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.display)

        return layout

    @staticmethod
    def _init_motion_builder(mb: MotionBuilder | None) -> MotionBuilder | None:
        if mb is not None and not isinstance(mb, MotionBuilder):
            raise TypeError(
                "Argument 'mb' must be None or an instance of MotionBuilder, "
                f"got type {type(mb)} instead."
            )

        return mb

    def _init_display(self) -> QWidget | _MSDBase:
        if self._mb is None:
            display = QWidget(parent=self)
        elif not isinstance(self._mb, MotionBuilder):
            raise RuntimeError(
                "Can not create a display for the motion space.  The "
                "motion builder is not the right type.  Expected type "
                f"MotionBuilder, but got type {type(self._mb)}.  "
            )
        elif self._mb.mspace_ndims == 2:
            display = MotionSpaceDisplay2D(logger=self._logger, mb=self._mb, parent=self)
            display.display_position = self._display_visibility["position"]
            display.display_target_position = self._display_visibility["target_position"]
            display.display_probe = self._display_visibility["probe"]
        else:
            raise RuntimeError(
                "Can not create a display for the motion space.  The "
                "motion builder has an unsupported dimenstioality.  Got "
                f"dimensionality {type(self._mb.mspace_ndims)}, but can only "
                f"support 2 or 3 dimensions."
            )

        display.setObjectName("motion_space_display")
        return display

    def _init_self(self):
        self.setStyleSheet("""
        MotionSpaceDisplay {
            border: 2px solid rgb(125, 125, 125);
            border-radius: 5px; 
            padding: 0px;
            margin: 0px;
        }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mb(self) -> MotionBuilder | None:
        return self._mb

    @property
    def display_position(self) -> bool:
        if not isinstance(self.display, _MSDBase):
            return self._display_visibility["position"]

        visibility = self.display.display_position
        self._display_visibility["position"] = visibility
        return visibility

    @display_position.setter
    def display_position(self, value: bool):
        if not isinstance(value, bool):
            return

        if not isinstance(self.display, _MSDBase):
            self._display_visibility["position"] = value
            return

        self.display.display_position = value
        self._display_visibility["position"] = self.display.display_position

    @property
    def display_target_position(self) -> bool:
        if not isinstance(self.display, _MSDBase):
            return self._display_visibility["target_position"]

        visibility = self.display.display_target_position
        self._display_visibility["target_position"] = visibility
        return visibility

    @display_target_position.setter
    def display_target_position(self, value: bool):
        if not isinstance(value, bool):
            return

        if not isinstance(self.display, _MSDBase):
            self._display_visibility["target_position"] = value
            return

        self.display.display_target_position = value
        self._display_visibility["target_position"] = self.display.display_target_position

    @property
    def display_probe(self) -> bool:
        if not isinstance(self.display, _MSDBase):
            return self._display_visibility["probe"]

        visibility = self.display.display_probe
        self._display_visibility["probe"] = visibility
        return visibility

    @display_probe.setter
    def display_probe(self, value: bool):
        if not isinstance(value, bool):
            return

        if not isinstance(self.display, _MSDBase):
            self._display_visibility["probe"] = value
            return

        self.display.display_probe = value
        self._display_visibility["probe"] = self.display.display_probe

    @property
    def is_animating_motion_list(self):
        if not isinstance(self.display, _MSDBase):
            return False

        return self.display.is_animating_motion_list

    def link_motion_builder(self, mb: MotionBuilder | None = None):
        self.logger.info(f"Linking motion builder {mb}")

        display_dimensionality = None
        if isinstance(self.display, _MSDBase):
            display_dimensionality = self.display.dimensionality

        new_mspace_dimensionality = None
        if isinstance(mb, MotionBuilder):
            new_mspace_dimensionality = mb.mspace_ndims

        if not isinstance(mb, MotionBuilder):
            mb = None

        if display_dimensionality is None and new_mspace_dimensionality is None:
            # nothing has changed
            self.unlink_motion_builder()
            return

        if (
            new_mspace_dimensionality is None
            or new_mspace_dimensionality == display_dimensionality
        ):
            self.unlink_motion_builder()
            self.display.link_motion_builder(mb)
            return

        if new_mspace_dimensionality != display_dimensionality:
            self.unlink_motion_builder()
            self._mb = mb
            self.display.setVisible(False)
            self._replace_display()

    def unlink_motion_builder(self):
        self.logger.info(f"Un-Linking motion builder.")
        self._mb = None

        if isinstance(self.display, _MSDBase):
            self.display.unlink_motion_builder()
            self.display.setVisible(False)

    def _replace_display(self):
        self.logger.info("Replacing the display widget")
        self._disconnect_display_signals()

        old_display = self.display
        new_display = self._init_display()
        self.layout().replaceWidget(old_display, new_display)

        old_display.blockSignals(True)
        old_display.setVisible(False)
        old_display.close()
        old_display.deleteLater()

        self.display = new_display
        self._connect_display_signals()

    def closeEvent(self, event: "QCloseEvent"):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)
