"""
Module contains all the main functionality for the |MotionGroup|
configuration portion of the configuration GUI.
"""
__all__ = ["MGWidget"]

import asyncio
import logging
import numpy as np
import os
import warnings

# ensure joystick events are monitored when the pygame window
# is not in focus ... this needs to be done before importing pygame
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

import pygame  # noqa

from abc import abstractmethod
from PySide6.QtCore import Qt, Signal, Slot, QRunnable, QSize, QThreadPool, QObject
from PySide6.QtGui import QDoubleValidator, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QLayout, QGridLayout,
)
from typing import Any, Dict, List, Optional, Tuple, Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.actors import Axis, Drive, MotionGroup, MotionGroupConfig, RunManager
from bapsf_motion.gui.configure import configure_
from bapsf_motion.gui.configure.bases import _ConfigOverlay, _OverlayWidget
from bapsf_motion.gui.configure.drive_overlay import DriveConfigOverlay
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.configure.motion_builder_overlay import MotionBuilderConfigOverlay
from bapsf_motion.gui.configure.motion_space_display import MotionSpaceDisplay
from bapsf_motion.gui.configure.transform_overlay import TransformConfigOverlay
from bapsf_motion.gui.widgets import (
    DiscardButton,
    DoneButton,
    GearValidButton,
    HLinePlain,
    IconButton,
    LED,
    QTAIconLabel,
    StyleButton,
    StopButton,
    ValidButton,
    ZeroButton,
)
from bapsf_motion.motion_builder import MotionBuilder
from bapsf_motion.transform import BaseTransform
from bapsf_motion.transform.helpers import transform_registry
from bapsf_motion.utils import _deepcopy_dict, loop_safe_stop, toml, dict_equal
from bapsf_motion.utils import units as u


class MSpaceMessageBox(QMessageBox):
    """
    Modal warning dialog box to warn the user the motion space has yet
    to be defined.  Thus, there are no restrictions on probe drive
    movement, and it is up to the user to prevent any collisions.
    """
    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._display_dialog = True

        self.setWindowTitle("Motion Space NOT Defined")
        self.setText(
            "Motion Space is NOT defined, so there are no restrictions "
            "on probe drive motion.  It is up to the user to avoid "
            "collisions.\n\n"
            "Proceed with movement?"
        )
        self.setIcon(QMessageBox.Icon.Warning)
        self.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Abort
        )
        self.setDefaultButton(QMessageBox.StandardButton.Abort)

        _cb = QCheckBox("Suppress future warnings for this motion group.")
        self.setCheckBox(_cb)

        self.checkBox().checkStateChanged.connect(self._update_display_dialog)

    @property
    def display_dialog(self) -> bool:
        return self._display_dialog

    @display_dialog.setter
    def display_dialog(self, value: bool) -> None:
        if not isinstance(value, bool):
            return

        # ensure the display boolean (display_dialog) is in sync
        # with the dialog check box ... these two values are supposed
        # to be NOTs of each other
        check_state = self.checkBox().checkState()
        if check_state is Qt.CheckState.Checked is value:
            self.checkBox().setChecked(not value)

        self._display_dialog = value

    @Slot(Qt.CheckState)
    def _update_display_dialog(self, state: Qt.CheckState) -> None:
        self.display_dialog = not (state is Qt.CheckState.Checked)

    def exec(self) -> bool:
        if not self.display_dialog:
            return True

        button = super().exec()

        if button == QMessageBox.StandardButton.Yes:
            # Make sure the Abort button always remains the default choice
            self.setDefaultButton(QMessageBox.StandardButton.Abort)
            return True
        elif button == QMessageBox.StandardButton.Abort:
            return False

        return False


class PyGameJoystickRunnerSignals(QObject):
    buttonPressed = Signal(int)
    hatPressed = Signal(int, int)
    axisMoved = Signal(int, float)
    joystickConnected = Signal(bool)
    shutdownLoop = Signal()


class PyGameJoystickRunner(QRunnable):
    # signals must be patterned in separate class, otherwise we can not
    # connect the signals in out __init__
    signals = PyGameJoystickRunnerSignals()

    def __init__(self, joystick: pygame.joystick.JoystickType):
        super().__init__()

        self._logger = gui_logger
        self._axis_dead_zone = 0.1
        self._run_loop = False

        # Re-instantiate the joystick since the given joystick was probably
        # instantiated in a different thread.
        joystick.init()
        js_id = joystick.get_id()
        joystick.quit()
        self._joystick = pygame.joystick.Joystick(js_id)

        self.signals.shutdownLoop.connect(self.run_shutdown)

    def run(self) -> None:
        self.logger.info("Starting PyGame Joystick runner")

        if not pygame.get_init():
            pygame.init()

        if not pygame.joystick.get_init():
            pygame.joystick.init()

        js = self.joystick
        if not isinstance(self.joystick, pygame.joystick.JoystickType):
            pygame.quit()
            return

        js.init()
        self.run_loop = js.get_init()
        self.signals.joystickConnected.emit(self.run_loop)

        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((100, 100), flags=pygame.HIDDEN)

        # pygame while loop
        # - joystick events
        #   https://www.pygame.org/docs/ref/event.html
        #
        #   JOYAXISMOTION
        #   JOYBALLMOTION
        #   JOYHATMOTION
        #   JOYBUTTONUP
        #   JOYBUTTONDOWN
        #   JOYDEVICEADDED
        #   JOYDEVICEREMOVED
        #
        # _joy_axis_values = {}
        while self.run_loop:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.run_loop = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    self.signals.buttonPressed.emit(event.dict["button"])

                    # TODO: add an immediate caller to handle emergency
                    #       stop scenarios
                elif event.type == pygame.JOYHATMOTION:
                    value = event.dict["value"]
                    axis_id = 0 if value[0] != 0 else 1
                    direction = value[axis_id]
                    self.signals.hatPressed.emit(axis_id, direction)

                elif event.type == pygame.JOYAXISMOTION:
                    axis = event.dict["axis"]
                    value = event.dict["value"]

                    self.signals.axisMoved.emit(axis, value)

                    # self.logger.info(
                    #     f"PyGame event {event.type} - Data = {event.dict}."
                    # )

            clock.tick(20)

        self.logger.info("PyGame loop ended.")
        self.run_shutdown()

    def run_shutdown(self):
        if self.run_loop:
            self.quit()
            self.signals.shutdownLoop.emit()
            return

        try:
            pygame.quit()
        except pygame.error as err:
            self.logger.warning(
                "The pygame event loop did not safely shut down and was "
                "forced to shut down.",
                exc_info=err,
            )

        self.signals.joystickConnected.emit(self.run_loop)

    @property
    def axis_dead_zone(self) -> float:
        return self._axis_dead_zone

    @axis_dead_zone.setter
    def axis_dead_zone(self, value: float) -> None:
        try:
            value = float(value)
        except TypeError:
            return

        if -1.0 >= value >= 1.0:
            self._axis_dead_zone = np.absolute(value)

    @property
    def joystick(self) -> pygame.joystick.JoystickType:
        return self._joystick

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def run_loop(self) -> bool:
        return self._run_loop

    @run_loop.setter
    def run_loop(self, value: bool) -> None:
        if isinstance(value, bool):
            self._run_loop = value

    def set_immediate_handler(self, func, event_type):
        ...

    def quit(self) -> None:
        if pygame.get_init():
            pygame.joystick.quit()
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.run_loop = False

        self.signals.joystickConnected.emit(self.run_loop)


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()
    movementStarted = Signal(int)
    movementStopped = Signal(int)
    axisStatusChanged = Signal()
    targetPositionChanged = Signal(float)

    def __init__(
        self,
        axis_display_mode="interactive",
        parent=None,
    ):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None
        self._axis_index = None

        if axis_display_mode not in ("interactive", "readonly"):
            self._logger.info(
                f"Forcing display mode of {self.__class__.__name__} to be"
                f" interactive."
            )
            axis_display_mode = "interactive"
        self._interactive_display_mode = (
            True if axis_display_mode == "interactive"
            else False
        )

        self.setFixedWidth(120)

        # Define BUTTONS
        _btn = IconButton("fa.arrow-up", parent=self)
        _btn.setIconSize(48)
        self.jog_forward_btn = _btn

        _btn = IconButton("fa.arrow-down", parent=self)
        _btn.setIconSize(48)
        self.jog_backward_btn = _btn

        _btn = ValidButton("FWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked"
        )
        self.limit_fwd_btn = _btn

        _btn = ValidButton("BWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked"
        )
        self.limit_bwd_btn = _btn

        _btn = StyleButton("HOME", parent=self)
        _btn.setEnabled(False)
        self.home_btn = _btn
        self.home_btn.setHidden(True)

        _btn = ZeroButton("ZERO", parent=self)
        self.zero_btn = _btn

        # Define TEXT WIDGETS
        _txt = QLabel("Name", parent=self)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setFixedHeight(18)
        self.axis_name_label = _txt

        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setReadOnly(True)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        self.position_label = _txt

        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        self.target_position_label = _txt

        _txt = QLineEdit("0", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        self.jog_delta_label = _txt

        # Define ADVANCED WIDGETS

        self.mspace_warning_dialog = None
        if hasattr(parent, "mspace_warning_dialog"):
            self.mspace_warning_dialog = parent.mspace_warning_dialog

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.jog_forward_btn.clicked.connect(self.jog_forward)
        self.jog_backward_btn.clicked.connect(self.jog_backward)
        self.zero_btn.clicked.connect(self._zero_axis)
        self.jog_delta_label.editingFinished.connect(self._validate_jog_value)
        self.target_position_label.editingFinished.connect(
            self._validate_target_position_value
        )

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if self.interactive_display_mode:
            layout = self._define_interactive_layout(layout)
        else:
            layout = self._define_readonly_layout()

        return layout

    def _define_interactive_layout(self, layout: QVBoxLayout = None):
        if layout is None:
            layout = QVBoxLayout()

        layout.addWidget(
            self.axis_name_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.position_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.target_position_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(self.limit_fwd_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.jog_forward_btn)
        layout.addStretch(1)
        layout.addWidget(self.jog_delta_label)
        layout.addWidget(self.home_btn)
        layout.addStretch(1)
        layout.addWidget(self.jog_backward_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.limit_bwd_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.zero_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)

        return layout

    def _define_readonly_layout(self, layout: QVBoxLayout = None):
        if layout is None:
            layout = QVBoxLayout()

        self.target_position_label.setEnabled(False)
        self.target_position_label.setVisible(False)

        self.jog_forward_btn.setEnabled(False)
        self.jog_forward_btn.setVisible(False)

        self.jog_backward_btn.setEnabled(False)
        self.jog_backward_btn.setVisible(False)

        self.home_btn.setEnabled(False)
        self.home_btn.setVisible(False)

        self.zero_btn.setEnabled(False)
        self.zero_btn.setVisible(False)

        self.limit_fwd_btn.setFixedHeight(24)
        self.limit_bwd_btn.setFixedHeight(24)

        self.jog_delta_label.setText("0.1")

        _fine_step_label = QLabel("Fine Step", parent=self)
        _font = _fine_step_label.font()
        _font.setPointSize(12)
        _fine_step_label.setFont(_font)

        layout.addWidget(
            self.axis_name_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addSpacing(4)
        layout.addWidget(self.limit_fwd_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addSpacing(8)
        layout.addWidget(
            self.position_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addSpacing(8)
        layout.addWidget(self.limit_bwd_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addSpacing(24)
        layout.addWidget(
            _fine_step_label,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBaseline,
        )
        layout.addWidget(self.jog_delta_label)
        layout.addStretch(1)

        return layout

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        return self._mg

    @property
    def axis_index(self) -> int:
        return self._axis_index

    @property
    def axis(self) -> Union[Axis, None]:
        if self.mg is None or self.axis_index is None:
            return None

        return self.mg.drive.axes[self.axis_index]

    @property
    def position(self) -> u.Quantity:
        position = self.mg.position
        val = position.value[self.axis_index]
        unit = position.unit
        return val * unit

    @property
    def target_position(self) -> Union[float, None]:
        try:
            pos = float(self.target_position_label.text())
        except ValueError:
            pos = None
        return pos

    @property
    def interactive_display_mode(self):
        return self._interactive_display_mode

    def _get_jog_delta(self):
        delta_str = self.jog_delta_label.text()
        return float(delta_str)

    def jog_forward(self):
        pos = self.position.value + self._get_jog_delta()
        self._move_to(pos)

    def jog_backward(self):
        pos = self.position.value - self._get_jog_delta()
        self._move_to(pos)

    def update_position_display(self, position: Union[u.Quantity, float]):
        if not isinstance(position, (u.Quantity, float)):
            return
        elif isinstance(position, u.Quantity):
            _txt = f"{position.value:.2f} {position.unit}"
        else:
            _txt = f"{position:.2f}"

        self.position_label.setText(_txt)

    def update_target_position_display(self, position):
        if not isinstance(position, (u.Quantity, float)):
            return
        elif isinstance(position, u.Quantity):
            _txt = f"{position.value:.2f} {position.unit}"
        else:
            _txt = f"{position:.2f}"

        self.target_position_label.setText(_txt)

    def _move_to(self, target_ax_pos):
        target_pos = self.mg.position.value
        target_pos[self.axis_index] = target_ax_pos

        if self.mg.drive.is_moving:
            self.logger.info(
                "Probe drive is currently moving.  Did NOT perform move "
                f"to {target_pos}."
            )
            return

        try:
            proceed = self.mspace_warning_dialog.exec()
        except AttributeError:
            proceed = False

        if proceed:
            self.mg.move_to(target_pos)

    def _update_display_of_axis_status(self):
        if self._mg.terminated:
            return

        if not self.isEnabled():
            return

        pos = self.position
        self.update_position_display(pos)
        if self.target_position_label.text() == "":
            self.update_position_display(pos)

        limits = self.axis.motor.status["limits"]
        self.limit_fwd_btn.set_valid(state=limits["CW"])
        self.limit_bwd_btn.set_valid(state=limits["CCW"])

    def _validate_jog_value(self):
        _txt = self.jog_delta_label.text()
        val = 0.0 if _txt == "" else float(_txt)
        val = abs(val)
        self.jog_delta_label.setText(f"{val:.2f}")

    def _validate_target_position_value(self):
        self.targetPositionChanged.emit(self.target_position)

    def _zero_axis(self):
        self.logger.info(f"Setting zero of axis {self.axis_index}")
        self.mg.set_zero(axis=self.axis_index)

    def link_axis(self, mg: MotionGroup, ax_index: int):
        if (
            not isinstance(ax_index, int)
            or ax_index < 0
            or ax_index >= len(mg.drive.axes)
        ):
            self.unlink_axis()
            return

        axis = mg.drive.axes[ax_index]
        if self.axis is not None and self.axis is axis:
            pass
        else:
            self.unlink_axis()

        self._mg = mg
        self._axis_index = ax_index

        self.axis_name_label.setText(self.axis.name)
        self.axis.motor.status_changed.connect(self._update_display_of_axis_status)
        self.axis.motor.status_changed.connect(self.axisStatusChanged.emit)
        self.axis.motor.movement_started.connect(self._emit_movement_started)
        self.axis.motor.movement_finished.connect(self._emit_movement_finished)
        self.axis.motor.movement_finished.connect(self._update_display_of_axis_status)
        self._update_display_of_axis_status()

        self.axisLinked.emit()

    def unlink_axis(self):
        if self.axis is not None:
            # self.axis.terminate(delay_loop_stop=True)
            self.axis.motor.status_changed.disconnect(self._update_display_of_axis_status)
            self.axis.motor.status_changed.connect(self.axisStatusChanged.emit)
            self.axis.motor.movement_started.connect(self._emit_movement_started)
            self.axis.motor.movement_finished.connect(self._emit_movement_finished)
            self.axis.motor.movement_finished.disconnect(
                self._update_display_of_axis_status
            )

        self._mg = None
        self._axis_index = None
        self.axisUnlinked.emit()

    def _emit_movement_started(self):
        self.movementStarted.emit(self.axis_index)

    def _emit_movement_finished(self):
        self.movementStopped.emit(self.axis_index)

    def enable_motion_buttons(self):
        self.zero_btn.setEnabled(True)
        self.jog_forward_btn.setEnabled(True)
        self.jog_backward_btn.setEnabled(True)

    def disable_motion_buttons(self):
        self.zero_btn.setEnabled(False)
        self.jog_forward_btn.setEnabled(False)
        self.jog_backward_btn.setEnabled(False)

    def closeEvent(self, event):
        self.logger.info("Closing AxisControlWidget")

        if isinstance(self.axis, Axis):
            self.axis.motor.status_changed.disconnect(self._update_display_of_axis_status)
            self.axis.motor.status_changed.disconnect(self.axisStatusChanged.emit)
            self.axis.motor.movement_started.disconnect(self._emit_movement_started)
            self.axis.motor.movement_finished.disconnect(self._emit_movement_finished)
            self.axis.motor.movement_finished.disconnect(
                self._update_display_of_axis_status
            )

        event.accept()


class DriveBaseController(QWidget):
    driveStatusChanged = Signal()
    movementStarted = Signal()
    movementStopped = Signal()
    moveTo = Signal(list)
    zeroDrive = Signal()
    targetPositionChanged = Signal(list)

    def __init__(self, axis_display_mode="interactive", parent=None):
        # axis_display_mode == "interactive" or "readonly"
        super().__init__(parent=parent)

        self._logger = gui_logger

        self._axis_display_mode = axis_display_mode
        self.mspace_warning_dialog = None
        if hasattr(parent, "mspace_warning_dialog"):
            self.mspace_warning_dialog = parent.mspace_warning_dialog

        self._mg = None
        self._mspace_drive_polarity = None

        self._axis_control_widgets = []  # type: List[AxisControlWidget]
        self._initialize_axis_control_widgets()

        self._initialize_widgets()

        self.setLayout(self._define_layout())
        self._connect_signals()

    @abstractmethod
    def _initialize_widgets(self):
        ...

    def _initialize_axis_control_widgets(self):
        for ii in range(4):
            acw = AxisControlWidget(
                axis_display_mode=self._axis_display_mode,
                parent=self,
            )
            visible = True if ii == 0 else False
            acw.setVisible(visible)
            self._axis_control_widgets.append(acw)

    def _connect_signals(self):
        self.movementStarted.connect(self.disable_motion_buttons)
        self.movementStopped.connect(self.enable_motion_buttons)

        for acw in self._axis_control_widgets:
            acw.targetPositionChanged.connect(self._target_position_changed)

    @abstractmethod
    def _define_layout(self) -> QLayout:
        ...

    @property
    def logger(self):
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        return self._mg

    @property
    def mspace_drive_polarity(self):
        return self._mspace_drive_polarity

    @property
    def position(self) -> List[float]:
        position = []
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            position.append(acw.position.value)

        return position

    @property
    def target_position(self) -> Union[List[float], None]:
        target_position = []
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            target_position.append(acw.target_position)

        if not bool(target_position):
            # no values in target position
            return None

        if any(pos is None for pos in target_position):
            # some target positions are not valid
            return None

        return target_position

    def _target_position_changed(self, position):
        self.logger.info(f"DBC target position changed {self.target_position}")
        tpos = self.target_position
        if tpos is None:
            tpos = []
        self.targetPositionChanged.emit(tpos)

    def link_motion_group(self, mg: MotionGroup):
        if not isinstance(mg, MotionGroup):
            self.logger.warning(
                f"Expected type {MotionGroup} for motion group, but got type"
                f" {type(mg)}."
            )

        if mg.drive is None:
            # drive has not been set yet
            self.unlink_motion_group()
            return
        elif (
                self.mg is not None
                and self.mg.drive is not None
                and mg.drive is self.mg.drive
        ):
            pass
        else:
            self.unlink_motion_group()
            self._mg = mg

        for ii, ax in enumerate(self.mg.drive.axes):
            acw = self._axis_control_widgets[ii]
            acw.link_axis(self.mg, ii)
            acw.movementStarted.connect(self._drive_movement_started)
            acw.movementStopped.connect(self._drive_movement_finished)
            acw.axisStatusChanged.connect(self.update_all_axis_displays)
            acw.axisStatusChanged.connect(self.driveStatusChanged.emit)
            acw.show()

        self.setEnabled(not self._mg.terminated)
        self._determine_mspace_drive_polarity()

    def unlink_motion_group(self):
        for ii, acw in enumerate(self._axis_control_widgets):
            visible = True if ii == 0 else False

            acw.unlink_axis()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                acw.movementStarted.disconnect(self._drive_movement_started)
                acw.movementStopped.disconnect(self._drive_movement_finished)
                acw.axisStatusChanged.disconnect(self.update_all_axis_displays)
                acw.axisStatusChanged.disconnect(self.driveStatusChanged.emit)

            acw.setVisible(visible)

        # self.mg.terminate(delay_loop_stop=True)
        self._mg = None
        self._mspace_drive_polarity = None
        self.setEnabled(False)

    def update_all_axis_displays(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue
            # elif acw.axis.is_moving:
            #     continue

            acw._update_display_of_axis_status()

    def disable_motion_buttons(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            acw.disable_motion_buttons()

    def enable_motion_buttons(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            acw.enable_motion_buttons()

    @Slot(int)
    def _drive_movement_started(self, axis_index):
        self.movementStarted.emit()

    @Slot(int)
    def _drive_movement_finished(self, axis_index):
        if not isinstance(self.mg, MotionGroup) or not isinstance(self.mg.drive, Drive):
            return

        is_moving = [ax.is_moving for ax in self.mg.drive.axes]
        is_moving[axis_index] = False
        if not any(is_moving):
            self.movementStopped.emit()

    def _determine_mspace_drive_polarity(self):
        naxes = self.mg.drive.naxes
        polarity = [1] * naxes
        mspace_zero = [0] * naxes
        drive_zero = self.mg.transform(mspace_zero, to_coords="drive")

        for ii in range(naxes):
            test_pt = [0] * naxes
            test_pt[ii] = 10
            drive_pt = self.mg.transform(test_pt, to_coords="drive")
            delta = drive_pt[0][ii] - drive_zero[0][ii]

            pt_polarity = 1 if delta > 0 else -1
            polarity[ii] = pt_polarity

        self._mspace_drive_polarity = polarity

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}.")

        for acw in self._axis_control_widgets:
            acw.close()

        event.accept()


class DriveDesktopController(DriveBaseController):
    def __init__(self, parent=None):
        super().__init__(axis_display_mode="interactive", parent=parent)

    def _initialize_widgets(self):
        # BUTTON WIDGETS
        _btn = StyleButton("Move \n To", parent=self)
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(100)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        self.move_to_btn = _btn

        _btn = StyleButton("Home \n All", parent=self)
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(100)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.home_btn = _btn
        self.home_btn.setVisible(False)

        _btn = ZeroButton("Zero \n All", parent=self)
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(100)
        _btn.setFont(font)
        self.zero_all_btn = _btn

    def _connect_signals(self):
        super()._connect_signals()

        self.zero_all_btn.clicked.connect(self.zeroDrive.emit)
        self.move_to_btn.clicked.connect(self._move_to)

    def _define_layout(self) -> QLayout:
        # Sub-Layout #1
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(self.move_to_btn)
        sub_layout.addStretch()
        sub_layout.addWidget(self.home_btn)
        sub_layout.addStretch()
        sub_layout.addWidget(self.zero_all_btn)

        # Sub-Layout #2
        _text = QLabel("Position", parent=self)
        font = _text.font()
        font.setPointSize(14)
        _text.setFont(font)
        _pos_label = _text

        _text = QLabel("Target", parent=self)
        font = _text.font()
        font.setPointSize(14)
        _text.setFont(font)
        _target_label = _text

        _text = QLabel("Jog Δ", parent=self)
        font = _text.font()
        font.setPointSize(14)
        _text.setFont(font)
        _jog_delta_label = _text

        sub_layout2 = QVBoxLayout()
        sub_layout2.setSpacing(8)
        sub_layout2.addSpacing(32)
        sub_layout2.addWidget(
            _pos_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addSpacing(6)
        sub_layout2.addWidget(
            _target_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addSpacing(108)
        sub_layout2.addWidget(
            _jog_delta_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addStretch(1)

        layout = QHBoxLayout()
        layout.addLayout(sub_layout)
        layout.addLayout(sub_layout2)
        for acw in self._axis_control_widgets:
            layout.addWidget(acw)
            layout.addSpacing(2)
        layout.addStretch()

        return layout

    def _move_to(self):
        target_pos = [
            acw.target_position
            for acw in self._axis_control_widgets
            if not acw.isHidden()
        ]

        if self.mg.drive.is_moving:
            self.logger.info(
                "Probe drive is currently moving.  Did NOT perform move "
                f"to {target_pos}."
            )
            target_pos = []

        if any(p is None for p in target_pos):
            self.logger.warning(
                f"Requested target position ({target_pos}) is not valid,"
                f" NOT performing move to."
            )
            return

        self.moveTo.emit(target_pos)

    def set_target_position(self, target_position: List[float]):
        npos = len(target_position)
        naxes = self.mg.drive.naxes

        if npos != naxes:
            self.logger.warning(
                f"Received target position {target_position} does NOT "
                f"have the same dimensionality as the drive "
                f"({naxes})."
            )
            return

        for ii, pos in enumerate(target_position):
            acw = self._axis_control_widgets[ii]
            acw.update_target_position_display(pos)

    def disable_motion_buttons(self):
        self.move_to_btn.setEnabled(False)
        self.zero_all_btn.setEnabled(False)

        super().disable_motion_buttons()

    def enable_motion_buttons(self):
        self.move_to_btn.setEnabled(True)
        self.zero_all_btn.setEnabled(True)

        super().enable_motion_buttons()


class DriveGameController(DriveBaseController):
    def __init__(self, parent=None):
        super().__init__(axis_display_mode="readonly", parent=parent)

    def _connect_signals(self):
        super()._connect_signals()

        self.refresh_controller_list_btn.clicked.connect(self.refresh_controller_combo)
        self.connect_btn.clicked.connect(self.connect_controller)
        self.controller_combo_widget.currentIndexChanged.connect(
            self.disconnect_controller
        )

    def _initialize_widgets(self):
        self._pygame_joystick_runner = None  # type: Union[PyGameJoystickRunner, None]
        self._thread_pool = QThreadPool(parent=self)

        # BUTTON WIDGETS
        _btn = StyleButton("Refresh List", parent=self)
        _btn.setFixedHeight(32)
        _font = _btn.font()
        _font.setPointSize(12)
        _btn.setFont(_font)
        self.refresh_controller_list_btn = _btn

        _btn = StyleButton("Connect", parent=self)
        _btn.setFixedHeight(32)
        _btn.setFont(_font)
        _btn.setFixedWidth(100)
        self.connect_btn = _btn

        # TEXT/ICON WIDGETS
        _led = LED(parent=self)
        _led.set_fixed_height(24)
        self.connected_led = _led

        # ADVANCED WIDGETS
        _combo = QComboBox(parent=self)
        _combo.setEditable(True)
        _combo.lineEdit().setReadOnly(True)
        _combo.lineEdit().setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        _combo.setFixedHeight(32)
        _combo.setFont(_font)
        self.controller_combo_widget = _combo

    def _define_layout(self) -> QLayout:
        self.refresh_controller_combo()

        connect_layout = QHBoxLayout()
        connect_layout.setContentsMargins(0, 0, 0, 0)
        connect_layout.addStretch(1)
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addWidget(self.connected_led)
        connect_layout.addStretch(1)

        _label_font = QFont()
        _label_font.setPointSize(12)
        _left_stick = QLabel("Left Stick :", parent=self)
        _left_stick.setFont(_label_font)
        _right_stick = QLabel("Right Stick :", parent=self)
        _right_stick.setFont(_label_font)
        _dpad_vert_stick = QLabel("DPad Up/Down :", parent=self)
        _dpad_vert_stick.setFont(_label_font)
        _dpad_horz_stick = QLabel("DPad Left/Right :", parent=self)
        _dpad_horz_stick.setFont(_label_font)
        _ab = QLabel("A / B :", parent=self)
        _ab.setFont(_label_font)
        _y = QLabel("Y :", parent=self)
        _y.setFont(_label_font)
        _move_y = QLabel("Move Y", parent=self)
        _move_y.setFont(_label_font)
        _move_x = QLabel("Move X", parent=self)
        _move_x.setFont(_label_font)
        _fine_y = QLabel("Fine Y", parent=self)
        _fine_y.setFont(_label_font)
        _fine_x = QLabel("Fine X", parent=self)
        _fine_x.setFont(_label_font)
        _stop = QLabel("STOP", parent=self)
        _stop.setFont(_label_font)
        _zero = QLabel("Zero", parent=self)
        _zero.setFont(_label_font)

        btn_label_layout = QGridLayout()
        btn_label_layout.setContentsMargins(0, 0, 0, 0)
        btn_label_layout.setColumnMinimumWidth(1, 8)
        btn_label_layout.addWidget(
            _left_stick, 0, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        btn_label_layout.addWidget(
            _right_stick, 1, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        btn_label_layout.addWidget(
            _dpad_vert_stick, 2, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        btn_label_layout.addWidget(
            _dpad_horz_stick, 3, 0, alignment=Qt.AlignmentFlag.AlignRight
        )
        btn_label_layout.addWidget(_ab, 4, 0, alignment=Qt.AlignmentFlag.AlignRight)
        btn_label_layout.addWidget(_y, 5, 0, alignment=Qt.AlignmentFlag.AlignRight)

        btn_label_layout.addWidget(_move_y, 0, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_label_layout.addWidget(_move_x, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_label_layout.addWidget(_fine_y, 2, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_label_layout.addWidget(_fine_x, 3, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_label_layout.addWidget(_stop, 4, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        btn_label_layout.addWidget(_zero, 5, 2, alignment=Qt.AlignmentFlag.AlignLeft)

        sub_layout_1 = QVBoxLayout()
        sub_layout_1.setContentsMargins(0, 0, 0, 0)
        sub_layout_1.addSpacing(16)
        sub_layout_1.addWidget(self.refresh_controller_list_btn)
        sub_layout_1.addWidget(self.controller_combo_widget)
        sub_layout_1.addLayout(connect_layout)
        sub_layout_1.addSpacing(24)
        sub_layout_1.addLayout(btn_label_layout)
        sub_layout_1.addStretch(1)

        sub_widget_1 = QWidget(parent=self)
        sub_widget_1.setLayout(sub_layout_1)
        sub_widget_1.setMaximumWidth(200)
        sub_widget_1.setMinimumWidth(100)
        sub_widget_1.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(sub_widget_1)
        layout.addSpacing(2)
        for acw in self._axis_control_widgets:
            layout.addWidget(acw)
            layout.addSpacing(2)
        layout.addStretch()

        return layout

    @property
    def available_controllers(self) -> List[pygame.joystick.JoystickType]:
        _joystick = pygame.joystick

        if not _joystick.get_init():
            _joystick.init()

        return [_joystick.Joystick(_id) for _id in range(_joystick.get_count())]

    @property
    def joystick(self) -> Union[pygame.joystick.JoystickType, None]:
        js_name = self.controller_combo_widget.currentText()
        self.logger.info(f"Selected joystick: {js_name} - {self.available_controllers}")
        js = None
        for _js in self.available_controllers:
            if _js.get_name() == js_name:
                js = _js
                break

        return js

    def refresh_controller_combo(self):
        self.disconnect_controller()

        current_controller_name = self.controller_combo_widget.currentText()

        self.controller_combo_widget.clear()

        controller_names = [
            controller.get_name()
            for controller in self.available_controllers
        ]
        controller_names.append("")
        self.controller_combo_widget.addItems(controller_names)

        if current_controller_name != "" and current_controller_name in controller_names:
            self.controller_combo_widget.setCurrentText(current_controller_name)
            self.connect_controller()
        else:
            self.controller_combo_widget.setCurrentText("")

    def connect_controller(self):
        self.logger.info("Connecting controller.")
        self._pygame_joystick_runner = PyGameJoystickRunner(self.joystick)

        self._pygame_joystick_runner.signals.joystickConnected.connect(
            self._update_connect_led
        )
        self._pygame_joystick_runner.signals.axisMoved.connect(
            self._handle_axis_move
        )
        self._pygame_joystick_runner.signals.buttonPressed.connect(
            self._handle_button_press
        )
        self._pygame_joystick_runner.signals.hatPressed.connect(
            self._handle_hat_press
        )

        self._thread_pool.start(self._pygame_joystick_runner)

    def disconnect_controller(self):
        if self._pygame_joystick_runner is None:
            return

        self._pygame_joystick_runner.quit()
        self._pygame_joystick_runner = None
        self._thread_pool.waitForDone(200)
        self._thread_pool.clear()

        if self.mg.is_moving:
            self.stop_move()

    def stop_move(self, axis=None, soft=False):
        self.logger.debug("Stopping move.")

        if axis is None:
            self.mg.stop(soft=soft)
            return

        try:
            self.mg.drive.send_command("stop", soft, axis=axis)
        except Exception:  # noqa
            self.mg.stop()

    def zero_drive(self):
        self.mg.set_zero()

    @Slot(bool)
    def _update_connect_led(self, value):
        self.connected_led.setChecked(value)

    @Slot(int, float)
    def _handle_axis_move(self, jaxis, value):
        if jaxis not in (1, 3):
            # moved joystick axis is not utilized
            return
        elif jaxis == 1:
            axis_id = 1
        else:  # jaxis == 3:
            axis_id = 0

        ax = self.mg.drive.axes[axis_id]

        if np.absolute(value) < 0.5:
            self.stop_move(axis=axis_id, soft=True)
        elif ax.is_moving:
            pass
        else:
            try:
                proceed = self.mspace_warning_dialog.exec()
            except AttributeError:
                proceed = False

            if not proceed:
                return

            # pygame up-down axes are inverted
            sign = 1 if value <= 0 else -1
            sign = self.mspace_drive_polarity[axis_id] * sign
            direction = "forward" if sign > 0 else "backward"

            self.mg.drive.send_command(
                "continuous_jog", direction, axis=axis_id
            )

    @Slot(int)
    def _handle_button_press(self, button):
        if button in (0, 1):
            self.stop_move()
        elif button == 3:
            self.zero_drive()

    @Slot(int, int)
    def _handle_hat_press(self, hat_id, direction):
        if direction == 0:
            # hat (dpad) button returned to unpressed state
            # do nothing
            return

        try:
            proceed = self.mspace_warning_dialog.exec()
        except AttributeError:
            proceed = False

        if not proceed:
            return

        acw = self._axis_control_widgets[hat_id]
        if direction > 0:
            acw.jog_forward()
        else:
            acw.jog_backward()

    def closeEvent(self, event):
        self.disconnect_controller()
        self._thread_pool.deleteLater()
        super().closeEvent(event)


class DriveControlWidget(QWidget):
    movementStarted = Signal()
    movementStopped = Signal()
    driveStatusChanged = Signal()
    targetPositionChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None

        self.setEnabled(True)
        self.setFixedHeight(450)

        # Define BUTTONS

        _btn = StopButton(parent=self)
        _btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        _btn.setFixedWidth(200)
        _btn.setMinimumHeight(400)
        font = _btn.font()
        font.setPointSize(32)
        font.setBold(True)
        _btn.setFont(font)
        self.stop_1_btn = _btn

        _btn = StopButton(parent=self)
        _btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        _btn.setFixedWidth(200)
        _btn.setMinimumHeight(400)
        font = _btn.font()
        font.setPointSize(32)
        font.setBold(True)
        _btn.setFont(font)
        self.stop_2_btn = _btn

        # Define TEXT WIDGETS
        # Define ADVANCED WIDGETS
        self.mspace_warning_dialog = MSpaceMessageBox(parent=self)
        self.desktop_controller_widget = DriveDesktopController(parent=self)
        self.game_controller_widget = None  # type: Union[DriveBaseController, None]
        self.stacked_controller_widget = QStackedWidget(parent=self)
        self.stacked_controller_widget.addWidget(self.desktop_controller_widget)

        _combo = QComboBox(parent=self)
        _font = _combo.font()
        _font.setPointSize(12)
        _combo.setEditable(True)
        _combo.lineEdit().setFont(_font)
        _combo.lineEdit().setReadOnly(True)
        _combo.lineEdit().setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        _combo.addItems(["Desktop", "Game Controller"])
        _combo.setFixedHeight(32)
        _combo.setFixedWidth(175)
        self.controller_combo_box = _combo

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.stop_1_btn.clicked.connect(self._stop_move)
        self.stop_2_btn.clicked.connect(self._stop_move)

        self.desktop_controller_widget.zeroDrive.connect(self._zero_drive)
        self.desktop_controller_widget.moveTo.connect(self._move_to)
        self.desktop_controller_widget.targetPositionChanged.connect(
            self.targetPositionChanged.emit
        )
        self.desktop_controller_widget.driveStatusChanged.connect(
            self.driveStatusChanged.emit
        )
        self.desktop_controller_widget.movementStarted.connect(
            self._drive_movement_started
        )
        self.desktop_controller_widget.movementStopped.connect(
            self._drive_movement_finished
        )

        self.controller_combo_box.currentTextChanged.connect(self._switch_stack)

    def _define_layout(self):

        # Define the central_banner_layout
        central_banner_layout = QHBoxLayout()
        central_banner_layout.setContentsMargins(0, 0, 0, 0)

        _label = QLabel("Control Mode:", parent=self)
        _label.setFixedHeight(32)
        _font = _label.font()
        _font.setPointSize(16)
        _label.setFont(_font)

        central_banner_layout.addStretch(1)
        central_banner_layout.addWidget(
            _label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        central_banner_layout.addSpacing(12)
        central_banner_layout.addWidget(
            self.controller_combo_box,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        central_banner_layout.addStretch(1)

        # Define the central_layout
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addLayout(central_banner_layout)
        central_layout.addWidget(HLinePlain(parent=self))
        central_layout.addWidget(self.stacked_controller_widget)

        # Main Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stop_1_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(central_layout)
        layout.addWidget(self.stop_2_btn, alignment=Qt.AlignmentFlag.AlignRight)
        return layout

    @property
    def logger(self):
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        return self._mg

    @property
    def position(self) -> List[float]:
        return self.desktop_controller_widget.position

    @property
    def target_position(self):
        return self.desktop_controller_widget.target_position

    def _stop_move(self):
        self.mg.stop()

    def _switch_stack(self):
        controller = self.controller_combo_box.currentText()
        _w = self.stacked_controller_widget.currentWidget()

        if (
            (controller == "Desktop" and isinstance(_w, DriveDesktopController))
            or (controller == "Game Controller" and isinstance(_w, DriveGameController))
        ):
            # no switch is needed
            pass
        elif controller == "Desktop":
            self.stacked_controller_widget.setCurrentIndex(0)
            self.stacked_controller_widget.removeWidget(_w)

            try:
                self.game_controller_widget.close()
                self.game_controller_widget.deleteLater()
            except AttributeError:
                pass

            self.game_controller_widget = None

        elif controller == "Game Controller":
            self.game_controller_widget = DriveGameController(parent=self)
            self.game_controller_widget.link_motion_group(self.mg)
            self.stacked_controller_widget.addWidget(self.game_controller_widget)
            self.stacked_controller_widget.setCurrentWidget(self.game_controller_widget)

        else:
            # should never happen
            pass

    def _zero_drive(self):
        self.mg.set_zero()

    def link_motion_group(self, mg):
        if not isinstance(mg, MotionGroup):
            self.logger.warning(
                f"Expected type {MotionGroup} for motion group, but got type"
                f" {type(mg)}."
            )
            self.unlink_motion_group()
            return

        if mg.drive is None:
            # drive has not been set yet
            self.unlink_motion_group()
            return
        else:
            self.unlink_motion_group()
            self._mg = mg

        self.setEnabled(not self._mg.terminated)
        if not self.isEnabled():
            return

        if isinstance(mg.mb, MotionBuilder):
            self.mspace_warning_dialog.display_dialog = False

        self.desktop_controller_widget.link_motion_group(self.mg)
        if self.game_controller_widget is not None:
            self.game_controller_widget.link_motion_group(self.mg)

        self.update_controller_displays()

    def unlink_motion_group(self):
        self.desktop_controller_widget.unlink_motion_group()
        if self.game_controller_widget is not None:
            self.game_controller_widget.unlink_motion_group()

        self._mg = None
        self.mspace_warning_dialog.display_dialog = True
        self.setEnabled(False)

    def update_controller_displays(self):
        self.desktop_controller_widget.update_all_axis_displays()
        if self.game_controller_widget is not None:
            self.game_controller_widget.update_all_axis_displays()

    def _drive_movement_started(self):
        self.controller_combo_box.setEnabled(False)
        self.movementStarted.emit()

    def _drive_movement_finished(self):
        self.controller_combo_box.setEnabled(True)
        self.movementStopped.emit()

    @Slot(list)
    def _move_to(self, target_pos):
        if not target_pos:
            # target_pos is an empty list
            return

        try:
            proceed = self.mspace_warning_dialog.exec()
        except AttributeError:
            proceed = False

        if proceed:
            self.mg.move_to(target_pos)

    def set_target_position(self, target_position: List[float]):
        npos = len(target_position)
        naxes = self.mg.drive.naxes

        if npos != naxes:
            self.logger.warning(
                f"Received target position {target_position} does NOT "
                f"have the same dimensionality as the drive "
                f"({naxes})."
            )
            return

        self.desktop_controller_widget.set_target_position(target_position)

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")

        self.desktop_controller_widget.close()

        if isinstance(self.game_controller_widget, QWidget):
            self.game_controller_widget.close()

        event.accept()


class MGWidget(QWidget):
    closing = Signal()
    configChanged = Signal()
    returnConfig = Signal(int, object)

    mg_loop = asyncio.new_event_loop()
    transform_registry = transform_registry

    def __init__(
        self,
        *,
        mg_config: Optional[MotionGroupConfig] = None,
        defaults: Optional[Dict[str, Any]] = None,
        parent: "configure_.ConfigureGUI",
    ):
        super().__init__(parent=parent)

        # Note: have to keep reference to parent, since (for some unknown
        #       reason) we are loosing reference to it...self.parent()
        #       eventually becomes a QStackedWidget ??
        self._parent = parent

        # gather deployed restricted values
        deployed_mg_names = []
        deployed_ips = []
        if isinstance(self._parent.rm, RunManager):
            for mg in self._parent.rm.mgs.values():
                if (
                    mg_config is not None
                    and mg_config["name"] == mg.config["name"]
                    and dict_equal(mg_config, mg.config)
                ):
                    # assume we are editing an existing motion group
                    continue

                deployed_mg_names.append(mg.config["name"])

                for axis in mg.drive.axes:
                    deployed_ips.append(axis.ip)

        self._deployed_restrictions = {
            "mg_names": deployed_mg_names,
            "ips": deployed_ips,
        }

        self._logger = logging.getLogger(f"{gui_logger.name}.MGW")

        self._mg = None
        self._mg_index = None

        self._mg_config = None
        if isinstance(mg_config, MotionGroupConfig):
            self._mg_config = _deepcopy_dict(mg_config)

        self._defaults = None if defaults is None else _deepcopy_dict(defaults)
        self._drive_defaults = None
        self._custom_drive_index = -1
        self._build_drive_defaults()

        self._transform_defaults = None
        self._build_transform_defaults()

        self._mb_defaults = None
        self._custom_mb_index = -1
        self._mb_combo_last_index = -1
        self._build_mb_defaults()

        # Define TEXT WIDGETS

        _widget = QTextEdit(parent=self)
        _widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        _widget.setReadOnly(True)
        _widget.font().setPointSize(14)
        _widget.font().setFamily("Courier New")
        _widget.setMinimumWidth(350)
        self.toml_widget = _widget

        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        self.mg_name_widget = _widget

        # Define BUTTONS

        _btn = DoneButton("Add / Update", parent=self)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = DiscardButton(parent=self)
        self.discard_btn = _btn

        _icon = QTAIconLabel("mdi.steering", parent=self)
        _icon.setFixedSize(32)
        _icon.setIconSize(24)
        self.drive_label = _icon

        _w = QComboBox(parent=self)
        _w.setEditable(False)
        font = _w.font()
        font.setPointSize(16)
        _w.setFont(font)
        _w.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._drive_dropdown = _w
        self._populate_drive_dropdown()

        _btn = GearValidButton(parent=self)
        self.drive_btn = _btn

        _icon.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        _icon = QTAIconLabel("mdi.motion", parent=self)
        _icon.setFixedSize(32)
        _icon.setIconSize(24)
        self.mb_label = _icon

        _w = QComboBox(parent=self)
        _w.setEditable(False)
        font = _w.font()
        font.setPointSize(16)
        _w.setFont(font)
        _w.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._mb_dropdown = _w
        self._populate_mb_dropdown()

        _btn = GearValidButton(parent=self)
        _btn.setEnabled(False)
        self.mb_btn = _btn

        _icon = QTAIconLabel("fa5s.exchange-alt", parent=self)
        _icon.setFixedSize(32)
        _icon.setIconSize(24)
        self.transform_label = _icon

        _w = QComboBox(parent=self)
        _w.setEditable(False)
        font = _w.font()
        font.setPointSize(16)
        _w.setFont(font)
        _w.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        _w.setIconSize(QSize(20, 20))
        _w.setToolTip(
            "Flagged items indicate the base transforms, which are not "
            "pre-configured."
        )
        _w.setToolTipDuration(30000)
        self._transform_dropdown = _w
        self._populate_transform_dropdown()

        _btn = GearValidButton(parent=self)
        _btn.setEnabled(False)
        self.transform_btn = _btn

        # Define ADVANCED WIDGETS
        self._overlay_widget = None  # type: Union[_ConfigOverlay, None]
        self._overlay_shown = False

        self.drive_control_widget = DriveControlWidget(parent=self)
        self.drive_control_widget.setEnabled(False)

        self.mpl_canvas = MotionSpaceDisplay(parent=self)
        _policy = self.mpl_canvas.sizePolicy()
        _policy.setRetainSizeWhenHidden(True)
        self.mpl_canvas.setSizePolicy(_policy)

        self.setLayout(self._define_layout())
        self._connect_signals()

        # if MGWidget launched without a drive then use a default
        # drive (if defined)
        if (
            "drive" not in self.mg_config
            and self.drive_defaults[0][0] != "Custom Drive"
        ):
            self._mg_config["drive"] = _deepcopy_dict(self.drive_defaults[0][1])

        # if MGWidget launched without a transform then use a default
        # transform
        if "transform" not in self.mg_config:
            self._populate_transform_dropdown()

            self.transform_dropdown.blockSignals(True)
            self.transform_dropdown.setCurrentIndex(0)
            self.transform_dropdown.blockSignals(False)

            tr_default_name = self.transform_dropdown.currentText()
            tr_config = {}
            for tr_name, tr_config in self.transform_defaults:
                if tr_name == tr_default_name:
                    break

            self._mg_config["transform"] = _deepcopy_dict(tr_config)

        # if MGWidget launched without a motion builder then use a default
        # motion builder
        if "motion_builder" not in self.mg_config:
            self.logger.info("INIT - Setting initial motion builder")
            self._populate_mb_dropdown()

            self.mb_dropdown.blockSignals(True)
            self.mb_dropdown.setCurrentIndex(0)
            self.mb_dropdown.blockSignals(True)

            mb_default_name = self.mb_dropdown.currentText()
            mb_config = {}
            for mb_name, mb_config in self.mb_defaults:
                if mb_name == mb_default_name:
                    break

            self._mg_config["motion_builder"] = _deepcopy_dict(mb_config)

        self._initial_mg_config = _deepcopy_dict(self._mg_config)

        if "name" not in self._mg_config or self._mg_config["name"] == "":
            self._mg_config["name"] = "A New MG"

        self.logger.info(f"Starting mg_config:\n {self._mg_config}")

        self._update_mg_name_widget()

        self._spawn_motion_group()
        self._refresh_drive_control()

    def _connect_signals(self):
        self.drive_btn.clicked.connect(self._popup_drive_configuration)
        self.transform_btn.clicked.connect(self._popup_transform_configuration)
        self.mb_btn.clicked.connect(self._popup_motion_builder_configuration)

        self.mg_name_widget.editingFinished.connect(self._rename_motion_group)

        self.configChanged.connect(self._config_changed_handler)

        self.drive_dropdown.currentIndexChanged.connect(
            self._drive_dropdown_new_selection
        )
        self.mb_dropdown.currentIndexChanged.connect(
            self._mb_dropdown_new_selection
        )
        self.transform_dropdown.currentIndexChanged.connect(
            self._transform_dropdown_new_selection
        )

        self.mpl_canvas.targetPositionSelected.connect(self._update_target_position)

        self.drive_control_widget.movementStarted.connect(self.disable_config_controls)
        self.drive_control_widget.movementStopped.connect(self.enable_config_controls)
        self.drive_control_widget.targetPositionChanged.connect(
            self.mpl_canvas.update_target_position_plot
        )
        self.drive_control_widget.driveStatusChanged.connect(
            self._update_position_in_plot
        )

        self.done_btn.clicked.connect(self.return_and_close)
        self.discard_btn.clicked.connect(self.close)

    def _update_position_in_plot(self):
        if self.drive_control_widget.isEnabled():
            position = self.drive_control_widget.position
        else:
            position = None
        self.mpl_canvas.update_position_plot(position)

    def _define_layout(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addLayout(self._define_mg_builder_layout(), 2)
        layout.addWidget(HLinePlain(parent=self))
        layout.addWidget(self.drive_control_widget)

        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()

        layout.addWidget(self.discard_btn)
        layout.addStretch()
        layout.addWidget(self.done_btn)

        return layout

    def _define_mg_builder_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._define_toml_layout())
        layout.addSpacing(8)
        layout.addWidget(self._define_central_builder_widget())
        layout.addSpacing(8)
        layout.addWidget(self.mpl_canvas)

        return layout

    def _define_toml_layout(self):
        label = QLabel("Motion Group Configuration", parent=self)
        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom
        )
        font = label.font()
        font.setPointSize(16)
        label.setFont(font)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.toml_widget)

        return layout

    def _define_central_builder_widget(self):

        _label = QLabel("Name:", parent=self)
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        name_label = _label

        title_sub_layout = QHBoxLayout()
        title_sub_layout.setContentsMargins(12, 0, 12, 0)
        title_sub_layout.addWidget(name_label)
        title_sub_layout.addSpacing(4)
        title_sub_layout.addWidget(self.mg_name_widget)

        drive_sub_layout = QHBoxLayout()
        drive_sub_layout.addWidget(self.drive_label)
        drive_sub_layout.addWidget(self.drive_dropdown)
        drive_sub_layout.addWidget(self.drive_btn)

        mb_sub_layout = QHBoxLayout()
        mb_sub_layout.addWidget(self.mb_label)
        mb_sub_layout.addWidget(self.mb_dropdown)
        mb_sub_layout.addWidget(self.mb_btn)

        transform_sub_layout = QHBoxLayout()
        transform_sub_layout.addWidget(self.transform_label)
        transform_sub_layout.addWidget(self.transform_dropdown)
        transform_sub_layout.addWidget(self.transform_btn)

        _legend_txt = QLabel("LEGEND", parent=self)
        font = _legend_txt.font()
        font.setBold(True)
        font.setPointSize(10)
        _legend_txt.setFont(font)

        valid_gear_legend_layout = QHBoxLayout()
        valid_gear_legend_layout.setContentsMargins(0, 0, 0, 0)
        _btn = GearValidButton(parent=self)
        _btn.set_valid()
        _btn.setFixedSize(24)
        _btn.setIconSize(20)
        valid_gear_legend_layout.addWidget(_btn)
        valid_gear_legend_layout.addSpacing(4)
        valid_gear_legend_layout.addWidget(
            QLabel("Configuration valid. Click to edit.", parent=self)
        )

        invalid_gear_legend_layout = QHBoxLayout()
        invalid_gear_legend_layout.setContentsMargins(0, 0, 0, 0)
        _btn = GearValidButton(parent=self)
        _btn.set_invalid()
        _btn.setFixedSize(24)
        _btn.setIconSize(20)
        invalid_gear_legend_layout.addWidget(_btn)
        invalid_gear_legend_layout.addSpacing(4)
        invalid_gear_legend_layout.addWidget(
            QLabel(
                "Configuration invalid. Click to edit.\nHover for tooltip.",
                parent=self,
            ),
        )

        drive_legend_layout = QHBoxLayout()
        drive_legend_layout.setContentsMargins(2, 0, 0, 0)
        _icon = QTAIconLabel("mdi.steering", parent=self)
        _icon.setFixedSize(20)
        _icon.setIconSize(20)
        drive_legend_layout.addWidget(_icon)
        drive_legend_layout.addSpacing(6)
        drive_legend_layout.addWidget(
            QLabel("Drive configuration.", parent=self)
        )

        mb_legend_layout = QHBoxLayout()
        mb_legend_layout.setContentsMargins(2, 0, 0, 0)
        _icon = QTAIconLabel("mdi.motion", parent=self)
        _icon.setFixedSize(20)
        _icon.setIconSize(20)
        mb_legend_layout.addWidget(_icon)
        mb_legend_layout.addSpacing(6)
        mb_legend_layout.addWidget(
            QLabel("Motion Builder / Space configuration.", parent=self)
        )

        tr_legend_layout = QHBoxLayout()
        tr_legend_layout.setContentsMargins(2, 0, 0, 0)
        _icon = QTAIconLabel("fa5s.exchange-alt", parent=self)
        _icon.setFixedSize(20)
        _icon.setIconSize(20)
        tr_legend_layout.addWidget(_icon)
        tr_legend_layout.addSpacing(6)
        tr_legend_layout.addWidget(
            QLabel("Transformer configuration.", parent=self)
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(18)
        layout.addLayout(title_sub_layout)
        layout.addSpacing(12)
        layout.addLayout(drive_sub_layout)
        layout.addLayout(mb_sub_layout)
        layout.addLayout(transform_sub_layout)
        layout.addSpacing(8)
        layout.addWidget(HLinePlain(parent=self))
        layout.addWidget(
            _legend_txt,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addLayout(valid_gear_legend_layout)
        layout.addLayout(invalid_gear_legend_layout)
        layout.addSpacing(4)
        layout.addLayout(drive_legend_layout)
        layout.addLayout(mb_legend_layout)
        layout.addLayout(tr_legend_layout)
        layout.addStretch()

        _widget = QWidget(parent=self)
        _widget.setLayout(layout)
        _widget.setFixedWidth(335)
        return _widget

    def _build_drive_defaults(self) -> List[Tuple[str, Dict[str, Any]]]:
        # Returned _drive_defaults is a List of Tuple pairs
        # - 1st Tuple element is the dropdown name
        # - 2nd Tuple element is the dictionary configuration
        if self._defaults is None or "drive" not in self._defaults:
            self._drive_defaults = [("Custom Drive", {})]
            self._custom_drive_index = 0
            return self._drive_defaults

        _drive_defaults = {"Custom Drive": {}}
        _defaults = _deepcopy_dict(self._defaults["drive"])  # type: dict
        default_name = _defaults.pop("default", "Custom Drive")

        # populate defaults dict
        if "name" in _defaults.keys():
            # only one drive defined
            _name = _defaults["name"]

            # exclude drives that are already deployed
            exclude = False
            ips = [ax["ip"] for ax in _defaults["axes"].values()]
            if (
                len(set(ips) - set(self._deployed_restrictions["ips"])) != len(ips)
            ):
                exclude = True

            # add to defaults
            if not exclude and _name not in _drive_defaults.keys():
                _drive_defaults[_name] = _deepcopy_dict(_defaults)
        else:
            for key, entry in _defaults.items():
                _name = entry["name"]

                # do not add duplicate defaults
                if _name in _drive_defaults.keys():
                    continue

                # exclude drives that are already deployed
                ips = [ax["ip"] for ax in entry["axes"].values()]
                if (
                    len(set(ips) - set(self._deployed_restrictions["ips"])) != len(ips)
                ):
                    continue

                # add to defaults
                _drive_defaults[_name] = _deepcopy_dict(entry)

        # convert to list of 2-element tuples
        self._drive_defaults = []
        for key, val in _drive_defaults.items():
            if key == default_name:
                self._drive_defaults.insert(0, (key, val))
            else:
                self._drive_defaults.append((key, val))
        self._custom_drive_index = 0 if default_name == "Custom Drive" else 1

        return self._drive_defaults

    def _build_mb_defaults(self):
        self._custom_mb_index = 0
        if self._defaults is None or "motion_builder" not in self._defaults:
            self._mb_defaults = [("Custom Motion Builder", {})]
            return self._mb_defaults

        _mb_defaults_dict = {"Custom Motion Builder": {}}
        _defaults = _deepcopy_dict(self._defaults["motion_builder"])
        default_name = _defaults.pop("default", "Custom Motion Builder")

        # populate defaults dict
        if "name" in _defaults:
            # only one mb defined
            _defaults = {0: _defaults}

        for key, entry in _defaults.items():
            if "name" not in entry:
                continue

            _name = entry["name"]
            if _name in _mb_defaults_dict or "space" not in entry:
                # do not add duplicate defaults
                continue

            try:
                mb = self._spawn_motion_builder(entry)

                if not isinstance(mb, MotionBuilder):
                    continue

                _mb_defaults_dict[_name] = _deepcopy_dict(mb.config)
                del mb
            except Exception:  # noqa
                continue

        # convert to list of 2-element tuples
        self._mb_defaults = []
        for key, val in _mb_defaults_dict.items():
            if key == default_name:
                self._mb_defaults.insert(0, (key, val))

                if key != "Custom Motion Builder":
                    self._custom_mb_index = 1
            else:
                self._mb_defaults.append((key, val))

        return self._mb_defaults

    def _build_transform_defaults(self):
        _defaults_dict = {}
        for tr_name in self.transform_registry.available_transforms:
            inputs = self.transform_registry.get_input_parameters(tr_name)
            _dict = {"type": tr_name}
            for key, val in inputs.items():
                _dict[key] = (
                    "" if val["param"].default is val["param"].empty
                    else val["param"].default
                )
            _defaults_dict[tr_name] = _dict

        default_key = "identity"
        if isinstance(self._defaults, dict) and "transform" in self._defaults:
            _defaults = _deepcopy_dict(self._defaults["transform"])
            default_key = _defaults.pop("default", default_key)

            if "name" in _defaults.keys():
                # only one transform defined
                _name = _defaults.pop("name")
                if "type" in _defaults or _defaults["type"] in _defaults_dict:
                    _type = _defaults["type"]
                    _defaults_dict[_name] = {
                        **_defaults_dict[_type], **_deepcopy_dict(_defaults)
                    }
            else:
                for key, val in _defaults.items():
                    if (
                        "name" not in val
                        or "type" not in val
                        or val["type"] not in _defaults_dict
                    ):
                        continue

                    _name = val.pop("name")
                    _type = val["type"]
                    _defaults_dict[_name] = {
                        **_defaults_dict[_type], **_deepcopy_dict(val)
                    }

        if default_key not in _defaults_dict:
            default_key = "identity"

        # convert to list of 2-element tuples
        self._transform_defaults = []
        for key, val in _defaults_dict.items():
            if key == default_key:
                self._transform_defaults.insert(0, (key, val))
            elif key == "identity":
                # Note: if default_key == "identity" then identity will be
                #       inserted at index 0
                self._transform_defaults.insert(1, (key, val))
            else:
                self._transform_defaults.append((key, val))

        return self._transform_defaults

    def _config_changed_handler(self):
        # Note: none of the methods executed here should cause a
        #       configChanged event
        self._validate_motion_group()

        # now update displays
        self._update_mg_name_widget()
        self._update_toml_widget()
        self._update_drive_dropdown()
        self._update_mb_dropdown()
        self._update_transform_dropdown()
        self._update_mpl_canvas_mb()

        # updating the drive control widget should always be the last
        # step
        self._update_drive_control_widget()

    def _populate_drive_dropdown(self):
        # always clear dropdown before population to prevent duplicating
        # an already populated dropdown
        self.drive_dropdown.clear()

        # populate
        for item in self.drive_defaults:
            drive_name = item[0]
            if drive_name == "Custom Drive":
                drive_name = item[1].get("name", "Custom Drive")

            self.drive_dropdown.addItem(drive_name)

        # set drive
        self.drive_dropdown.blockSignals(True)
        drive_index = 0
        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            drive_name = self.mg.drive.config["name"]
            drive_index = self.drive_dropdown.findText(drive_name)
        self.drive_dropdown.setCurrentIndex(drive_index)

        self.drive_dropdown.blockSignals(False)

    def _populate_mb_dropdown(self):
        self.logger.info("Populating Motion Builder dropdown")

        mb_name_stored = (
            None if self.mb_dropdown.count() == 0
            else self.mb_dropdown.currentText()
        )

        # Block signals when repopulating the dropdown
        self.mb_dropdown.blockSignals(True)

        self.mb_dropdown.clear()

        # get space dimensionality
        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            naxes = self.mg.drive.naxes
        elif "drive" in self.mg_config and "axes" in self.mg_config["drive"]:
            naxes = len(self.mg_config["drive"]["axes"])
        else:
            naxes = -1

        # populate dropdown
        for mb_name, mb_config in self.mb_defaults:
            index = self.mb_dropdown.findText(mb_name)
            if index != -1:
                # motion builder already in dropdown
                continue

            if mb_name == "Custom Motion Builder":
                pass
            elif naxes == -1:
                # drive is not validated, so we do not know its dimensionality
                # we can only allow 'Custom Motion Builder' at this point
                continue
            elif naxes != len(mb_config["space"]):
                # mb dimensionality does not match drive dimensionality
                continue

            self.mb_dropdown.addItem(mb_name)

        if mb_name_stored is not None:
            index = self.mb_dropdown.findText(mb_name_stored)

            if index != -1:
                self._mb_combo_last_index = index
                self.mb_dropdown.setCurrentIndex(index)
                self.mb_dropdown.blockSignals(False)
                return

        self.mb_dropdown.blockSignals(False)

        # set default transform
        if (
            "motion_builder" in self.mg_config
            and bool(self.mg_config["motion_builder"])
        ):
            _config = _deepcopy_dict(self.mg_config["motion_builder"])
            pass
        elif (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mg.mb, MotionBuilder)
        ):
            self._mb_combo_last_index = 0
            self.mb_dropdown.setCurrentIndex(0)
            return
        else:
            _config = _deepcopy_dict(self.mg.mb.config)

        for mb_name, mb_default_config in self.mb_defaults:
            if mb_name == "Custom Motion Builder":
                continue

            if dict_equal(_deepcopy_dict(_config), mb_default_config):
                index = self.mb_dropdown.findText(mb_name)
                if index == -1:
                    # this should not happen
                    break

                self._mb_combo_last_index = index
                self.mb_dropdown.setCurrentIndex(index)
                return

        index = self.mb_dropdown.findText("Custom Motion Builder")
        self._mb_combo_last_index = index
        self.mb_dropdown.setCurrentIndex(index)

    def _populate_transform_dropdown(self):

        tr_name_stored = None
        tr_config_stored = None
        if self.transform_dropdown.count() != 0:
            # we are repopulating and need to reset dropdown to current position
            tr_name_stored = self.transform_dropdown.currentText()
            tr_config_stored = None
            for _name, _config in self.transform_defaults:
                if _name == tr_name_stored:
                    tr_config_stored = _config
                    break

        # Block signals when repopulating the dropdown
        self.transform_dropdown.blockSignals(True)

        self.transform_dropdown.clear()

        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            naxes = self.mg.drive.naxes
        elif "drive" in self.mg_config and "axes" in self.mg_config["drive"]:
            naxes = len(self.mg_config["drive"]["axes"])
        else:
            naxes = -1
        allowed_transforms = self.transform_registry.get_names_by_dimensionality(naxes)

        # populate dropdown
        _template_icon = qta.icon("mdi6.map-marker-star-outline")
        for tr_name, tr_config in self.transform_defaults:
            index = self.transform_dropdown.findText(tr_name)
            if index != -1:
                # transform already in dropdown
                continue

            if (
                "type" not in tr_config
                or tr_config["type"] not in allowed_transforms
            ):
                continue

            self.transform_dropdown.addItem(tr_name)

            # add icon for base/template transforms
            if tr_name == tr_config["type"]:
                count = self.transform_dropdown.count()
                self.transform_dropdown.setItemIcon(count-1, _template_icon)

        if (
            isinstance(self.mg, MotionGroup)
            and isinstance(self.mg.transform, BaseTransform)
        ):
            _type = self.mg.transform.transform_type
            _config = _deepcopy_dict(self.mg.transform.config)
            if (
                tr_config_stored is None
                or tr_config_stored["type"] != _type
                or not dict_equal(tr_config_stored, _config)
            ):
                tr_name_stored = _type

            for ii, _item in enumerate(self.transform_defaults):
                tr_name = _item[0]
                tr_default_config = _item[1]

                if tr_name_stored != tr_default_config["type"]:
                    continue

                index = self.transform_dropdown.findText(tr_name)
                if index == -1:
                    # this should not happen
                    break

                self._transform_defaults[ii] = (
                    tr_name,
                    {**tr_default_config, **_config},
                )
                self.transform_dropdown.setCurrentIndex(index)
                self.transform_dropdown.blockSignals(False)
                return

        if tr_name_stored is not None:
            index = self.transform_dropdown.findText(tr_name_stored)

            if index != -1:
                self.transform_dropdown.setCurrentIndex(index)
                self.transform_dropdown.blockSignals(False)
                return

        self.transform_dropdown.blockSignals(False)

        # set default transform
        self.transform_dropdown.setCurrentIndex(0)

    def _popup_drive_configuration(self):
        self._overlay_setup(
            DriveConfigOverlay(self.mg, parent=self)
        )

        # overlay signals
        self._overlay_widget.returnConfig.connect(self._change_drive)
        self._overlay_widget.discard_btn.clicked.connect(self._rerun_drive)

        self._overlay_widget.show()
        self._overlay_shown = True

    def _popup_transform_configuration(self):
        self._overlay_setup(
            TransformConfigOverlay(self.mg, parent=self)
        )

        # overlay signals
        self._overlay_widget.returnConfig.connect(self._change_transform)

        self._overlay_widget.show()
        self._overlay_shown = True

    def _popup_motion_builder_configuration(self):
        self._overlay_setup(
            MotionBuilderConfigOverlay(self.mg, parent=self)
        )

        # overlay signals
        self._overlay_widget.returnConfig.connect(self._change_motion_builder)

        self._overlay_widget.show()
        self._overlay_shown = True

    def _overlay_setup(self, overlay: "_OverlayWidget"):
        overlay.move(0, 0)
        overlay.resize(self.width(), self.height())
        overlay.closing.connect(self._overlay_close)

        self._overlay_widget = overlay

    def _overlay_close(self):
        self._overlay_widget.deleteLater()
        self._overlay_widget = None
        self._overlay_shown = False

    def resizeEvent(self, event):
        if self._overlay_shown:
            self._overlay_widget.resize(event.size())
        super().resizeEvent(event)

    @property
    def drive_dropdown(self) -> QComboBox:
        return self._drive_dropdown

    @property
    def mb_dropdown(self) -> QComboBox:
        return self._mb_dropdown

    @property
    def transform_dropdown(self) -> QComboBox:
        return self._transform_dropdown

    @property
    def drive_defaults(self) -> List[Tuple[str, Dict[str, Any]]]:
        return self._drive_defaults

    @property
    def mb_defaults(self) -> List[Tuple[str, Dict[str, Any]]]:
        return self._mb_defaults

    @property
    def transform_defaults(self) -> List[Tuple[str, Dict[str, Any]]]:
        return self._transform_defaults

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg_index(self):
        return self._mg_index

    @mg_index.setter
    def mg_index(self, val):
        self._mg_index = val

    @property
    def mg(self) -> "MotionGroup":
        """Current working Motion Group"""
        return self._mg

    def _set_mg(self, mg: Union[MotionGroup, None]):
        if not (isinstance(mg, MotionGroup) or mg is None):
            return

        self._mg = mg
        self.configChanged.emit()

    @property
    def mg_config(self) -> Union[Dict[str, Any], "MotionGroupConfig"]:
        if isinstance(self.mg, MotionGroup):
            self._mg_config = self.mg.config
            return self._mg_config
        elif self._mg_config is None:
            name = self.mg_name_widget.text()
            self._mg_config = {"name": name}

        return self._mg_config

    @Slot(object)
    def _change_drive(self, config: Dict[str, Any]):
        self.logger.info(f"Replacing the motion group's drive with config...\n{config}")
        mg_config = _deepcopy_dict(self.mg_config)
        mg_config["drive"] = _deepcopy_dict(config)
        self._mg_config = mg_config

        self._spawn_motion_group()

        self.mb_btn.setEnabled(True)
        self.transform_btn.setEnabled(True)

        if self.mg.transform is None:
            self.mg.replace_transform({"type": "identity"})

        self._refresh_drive_control()
        self.configChanged.emit()

    @Slot(object)
    def _change_transform(self, config: Dict[str, Any]):
        self.logger.info(f"Replacing the motion group's transform...\n{config}")
        if not bool(config):
            # config is empty
            self.drive_control_widget.setEnabled(False)
            self.transform_btn.set_invalid()

        self.mg.replace_transform(_deepcopy_dict(config))

        self.configChanged.emit()

    @Slot(object)
    def _change_motion_builder(self, config: Dict[str, Any]):
        self.logger.info(f"Replacing the motion group's motion builder.\n{config}")
        self.mg.replace_motion_builder(_deepcopy_dict(config))
        self.configChanged.emit()

    def _rerun_drive(self):
        self.logger.info("Restarting the motion group's drive")

        if not isinstance(self.mg, MotionGroup) or self.mg.drive is None:
            return

        drive_config = self.mg.drive.config
        self._change_drive(drive_config)

    def _refresh_drive_control(self):
        self.logger.info("Refreshing drive control widget.")
        if self.mg is None or self.mg.drive is None:
            self.drive_control_widget.unlink_motion_group()
            return

        self.drive_control_widget.link_motion_group(self.mg)

        target_position = self.drive_control_widget.target_position
        self.drive_control_widget.targetPositionChanged.emit(target_position)

    def _update_drive_dropdown(self):
        if self._custom_drive_index == -1:
            # this should never happen if self._custom_drive_index was
            # defined properly
            raise ValueError("Custom Drive not found")
        custom_drive_index = self._custom_drive_index

        if "drive" not in self.mg_config:
            self.drive_dropdown.setCurrentIndex(custom_drive_index)
            return

        drive_config = self.mg_config["drive"]
        if "name" not in drive_config:
            # this could happen if MGWidget is instantiated with an
            # invalid drive config or None
            self.drive_dropdown.setCurrentIndex(custom_drive_index)
            return
        name = drive_config["name"]
        index = self.drive_dropdown.findText(name)

        if index == -1:
            self.drive_dropdown.setCurrentIndex(custom_drive_index)
            return

        self.drive_dropdown.setCurrentIndex(index)

    def _update_mb_dropdown(self):
        self.logger.info("Updating MB dropdown")
        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.mb, MotionBuilder):
            mb_config = _deepcopy_dict(self.mg.mb.config)
            mb_dropdown_index = self.mb_dropdown.currentIndex()
            mb_dropdown_name = self.mb_defaults[mb_dropdown_index][0]
            mb_dropdown_config = self.mb_defaults[mb_dropdown_index][1]

            if mb_dropdown_name == "Custom Motion Builder":
                # update the custom motion builder with the current config
                self.mb_defaults[mb_dropdown_index] = (mb_dropdown_name, mb_config)
            elif dict_equal(mb_config, mb_dropdown_config):
                # the config for the pre-defined motion builder matches the
                # deployed config
                pass
            else:
                # the config for the pre-defined motion builder does NOT match
                # the deployed config...switch to custom motion builder
                self.mb_dropdown.blockSignals(True)

                self.mb_defaults[self._custom_mb_index] = (
                    "Custom Motion Builder", mb_config
                )

                self._mb_combo_last_index = self._custom_mb_index
                self.mb_dropdown.setCurrentIndex(self._custom_mb_index)

                self.mb_dropdown.blockSignals(False)

        self._populate_mb_dropdown()

    def _update_transform_dropdown(self):
        self._populate_transform_dropdown()

    def _update_toml_widget(self):
        self.toml_widget.setText(toml.as_toml_string(self.mg_config))

    def _update_mg_name_widget(self):
        self.mg_name_widget.setText(self.mg_config["name"])

    def _update_drive_control_widget(self):
        if not self.drive_control_widget.isEnabled():
            return

        self._refresh_drive_control()

    def _update_mpl_canvas_mb(self):
        if (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mg.mb, MotionBuilder)
        ):
            self.mpl_canvas.unlink_motion_builder()
            return

        if not isinstance(self.mpl_canvas.mb, MotionBuilder):
            self.mpl_canvas.link_motion_builder(self.mg.mb)
            return

        if dict_equal(self.mg.mb.config, self.mpl_canvas.mb.config):
            # canvas already had current motion builder
            return

        self.mpl_canvas.link_motion_builder(self.mg.mb)

    @Slot(list)
    def _update_target_position(self, target_position: List[float]):
        self.drive_control_widget.set_target_position(target_position)

    def _rename_motion_group(self):
        self.logger.info("Renaming motion group")
        self.mg.config["name"] = self.mg_name_widget.text()
        self.configChanged.emit()

    @staticmethod
    def _spawn_motion_builder(config: Dict[str, Any]) -> Union[MotionBuilder, None]:
        """Return an instance of |MotionBuilder|."""
        if config is None or not config:
            return None

        # initialize the motion builder object
        mb_config = config.copy()

        for key in {"name", "user"}:
            mb_config.pop(key, None)

        _inputs = {}
        for key, _kwarg in zip(
                ("space", "layer", "exclusion"),
                ("space", "layers", "exclusions"),
        ):
            try:
                _inputs[_kwarg] = list(mb_config.pop(key).values())
            except KeyError:
                continue

        return MotionBuilder(**_inputs)

    def _spawn_motion_group(self):
        self.logger.info("Spawning Motion Group")

        if isinstance(self.mg, MotionGroup):
            self.logger.info("Terminating Motion Group for re-spawn.")
            self.mg.terminate(delay_loop_stop=True)
            # self._set_mg(None)
            self._mg = None

        mg = None
        try:
            mg = MotionGroup(
                config=self.mg_config,
                logger=logging.getLogger(f"{self.logger.name}.MG"),
                loop=self.mg_loop,
                auto_run=True,
            )
        except (ConnectionError, TimeoutError, ValueError, TypeError) as err:
            self.logger.warning(
                "Not able to instantiate MotionGroup.",
                exc_info=err,
            )
            try:
                mg.terminate(delay_loop_stop=True)
            except AttributeError:
                pass

            mg = None

        # modify drive_dropdown
        drive_name = (
            "Custom Drive"
            if not (isinstance(mg, MotionGroup) and isinstance(mg.drive, Drive))
            else mg.drive.config["name"]
        )
        drive_entry = (
            {} if drive_name == "Custom Drive"
            else _deepcopy_dict(mg.drive.config)
        )
        dd_index = self.drive_dropdown.findText(drive_name)
        if dd_index == -1:
            # reset/define custom drive entry
            for _default in self.drive_defaults:
                self._drive_defaults[self._custom_drive_index] = (
                    "Custom Drive", drive_entry
                )
            self.drive_dropdown.blockSignals(True)
            self._populate_drive_dropdown()
            self.drive_dropdown.blockSignals(False)
            # Note: self._set_mg() should trigger self._update_drive_dropdown()
            #       so we are not explicitly setting the dropdown index here

        self._set_mg(mg)

        return mg

    def _validate_motion_group(self):
        self.logger.info("Validating motion group")

        vmg_name = self._validate_motion_group_name()
        vdrive = self._validate_drive()

        # Enable / Disable Motion Builder Config
        self.mb_dropdown.setEnabled(vdrive)
        self.mb_btn.setEnabled(vdrive)

        # Enable / Disable Transformer Config
        self.transform_dropdown.setEnabled(vdrive)
        self.transform_btn.setEnabled(vdrive)

        if not isinstance(self.mg, MotionGroup):
            mb = None
            transform = None
        else:
            mb = self.mg.mb
            transform = self.mg.transform

        if not isinstance(mb, MotionBuilder):
            self.mb_btn.set_invalid()
            self.mb_btn.setToolTip("Motion space needs to be defined.")
            self.done_btn.setEnabled(False)
        elif "layer" not in mb.config:
            self.mb_btn.set_invalid()
            self.mb_btn.setToolTip(
                "A point layer needs to be defined to generate a motion list."
            )
        else:
            self.mb_btn.set_valid()
            self.mb_btn.setToolTip("")

        if not isinstance(transform, BaseTransform):
            self.transform_btn.set_invalid()
            self.transform_btn.setToolTip("Transformer needs to be fully configured.")

            self.done_btn.setEnabled(False)
            self.drive_control_widget.setEnabled(False)
        else:
            self.transform_btn.set_valid()
            self.transform_btn.setToolTip("")

            self.drive_control_widget.setEnabled(True)

        if (
            self.drive_btn.is_valid
            and self.mb_btn.is_valid
            and self.transform_btn.is_valid
            and vmg_name
            and vdrive
        ):
            self.done_btn.setEnabled(True)
        else:
            self.done_btn.setEnabled(False)

    def _validate_motion_group_name(self) -> bool:
        mg_name = self.mg_name_widget.text()
        self.logger.info(f"Validating motion group name '{mg_name}'.")

        # clear previous tooltips and actions
        self.mg_name_widget.setToolTip("")
        for action in self.mg_name_widget.actions():
            self.mg_name_widget.removeAction(action)

        if mg_name == "":
            self.mg_name_widget.addAction(
                qta.icon("fa5.window-close", color="red"),
                QLineEdit.ActionPosition.LeadingPosition,
            )
            self.mg_name_widget.setToolTip("Must enter a non-null name.")
            return False

        if mg_name in self._deployed_restrictions["mg_names"]:
            self.mg_name_widget.addAction(
                qta.icon("fa5.window-close", color="red"),
                QLineEdit.ActionPosition.LeadingPosition,
            )
            deployed_mg_names = [
                f"'{name}'" for name in self._deployed_restrictions["mg_names"]
            ]
            self.mg_name_widget.setToolTip(
                "Motion group must have a unique name.  The following names "
                f"are already in used {', '.join(deployed_mg_names)}."
            )
            return False

        return True

    def _validate_drive(self) -> bool:
        self.drive_btn.setToolTip("")

        if not isinstance(self.mg, MotionGroup) or not isinstance(self.mg.drive, Drive):
            self.done_btn.setEnabled(False)

            self.drive_btn.set_invalid()
            self.drive_control_widget.setEnabled(False)

            self.drive_btn.setToolTip("Drive is not fully configured.")
            return False

        self.drive_dropdown.setEnabled(True)
        self.drive_btn.setEnabled(True)

        if self.mg.drive.terminated:
            self.drive_btn.set_invalid()
            self.drive_control_widget.setEnabled(False)
            self.done_btn.setEnabled(False)
            self.drive_btn.setToolTip(
                "Drive is terminated (i.e. not running). Try re-configuring."
            )
            return False

        shared_ips = []
        for ax in self.mg.drive.axes:
            if ax.ip in self._deployed_restrictions["ips"]:
                shared_ips.append(ax.ip)

        if len(shared_ips) != 0:
            self.drive_btn.set_invalid()
            self.drive_btn.setToolTip(
                "Configured drive shares IPs with drives that are already deployed.  "
                f"Shared IPS are {', '.join(shared_ips)}"
            )
            return False

        self.drive_btn.set_valid()
        return True

    @Slot(int)
    def _drive_dropdown_new_selection(self, index):
        if index == -1:
            self.logger.warning(f"Selected index {index} in drive dropdown is invalid.")
            return

        self.logger.warning(f"New selections in drive dropdown {index}")

        drive_config = _deepcopy_dict(self.drive_defaults[index][1])
        self._change_drive(drive_config)

    @Slot(int)
    def _mb_dropdown_new_selection(self, index):

        if index == -1:
            self.logger.warning(f"Selected index {index} in mb dropdown is invalid.")
            return
        elif index == self._mb_combo_last_index:
            # index did not change
            return

        self._mb_combo_last_index = index

        mb_dropdown_name = self.mb_dropdown.currentText()
        mb_dropdown_config = _deepcopy_dict(self.mb_defaults[index][1])
        self.logger.warning(
            f"New selections in motion builder dropdown {index} '{mb_dropdown_name}'"
        )

        self._change_motion_builder(mb_dropdown_config)

    @Slot(int)
    def _transform_dropdown_new_selection(self, index):
        tr_name = self.transform_dropdown.currentText()
        self.logger.info(f"New selections in transform dropdown {index} '{tr_name}'")

        if index == -1:
            return

        tr_default_config = None  # type: Union[Dict[str, Any], None]
        for _name, _config in self.transform_defaults:
            if tr_name != _name:
                continue

            tr_default_config = _deepcopy_dict(_config)
            break

        if tr_default_config is None:
            # could not find the default config
            self._update_transform_dropdown()
            return
        elif (
            tr_name == tr_default_config["type"]
            and any(val == "" for val in tr_default_config.values())
        ):
            # This is a not fully defined transform type
            self._change_transform({})
            return
        elif (
            "transform" in self.mg_config
            and "type" in self.mg_config["transform"]
            and tr_default_config["type"] == self.mg_config["transform"]["type"]
            and dict_equal(tr_default_config, _deepcopy_dict(self.mg_config["transform"]))
        ):
            # selected transform is already deployed
            return

        self._change_transform(tr_default_config)

    def disable_config_controls(self):
        self.drive_dropdown.setEnabled(False)
        self.drive_btn.setEnabled(False)

        self.mb_dropdown.setEnabled(False)
        self.mb_btn.setEnabled(False)

        self.transform_dropdown.setEnabled(False)
        self.transform_btn.setEnabled(False)

    def enable_config_controls(self):
        self._validate_motion_group()

    def return_and_close(self):
        config = _deepcopy_dict(self.mg.config)
        index = -1 if self._mg_index is None else self._mg_index

        self.logger.info(
            f"New MotionGroup configuration is being returned, {config}."
        )

        # Terminate MG before returning config, so we do not risk having
        # conflicting MGs communicating with the motors
        if isinstance(self.mg, MotionGroup) and not self.mg.terminated:
            # disable the Drive control widget, so we do not risk creating
            # extra events while terminating
            self.drive_control_widget.setEnabled(False)
            self.mg.terminate(delay_loop_stop=True)

        self.returnConfig.emit(index, config)
        self.close()

    def closeEvent(self, event):
        self.logger.info("Closing MGWidget")
        try:
            self.configChanged.disconnect()
        except RuntimeError:
            pass

        # disable the Drive control widget, so we do not risk creating
        # extra events while terminating
        self.drive_control_widget.setEnabled(False)

        if isinstance(self.mg, MotionGroup) and not self.mg.terminated:
            self.mg.terminate(delay_loop_stop=True)

        if self._overlay_widget is not None:
            self._overlay_widget.close()

        self.drive_control_widget.close()

        loop_safe_stop(self.mg_loop)
        self.closing.emit()
        event.accept()
