"""
Module containing "controller" classes that control the actual movement
of the probe dirves (i.e. motion groups).
"""

__all__ = ["DriveDesktopController", "DriveGameController"]

import logging
import numpy as np
import os
import re
import warnings

# ensure joystick events are monitored when the pygame window
# is not in focus ... this needs to be done before importing pygame
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"  # noqa

import pygame  # noqa

from abc import ABC, abstractmethod
from PySide6.QtCore import Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDoubleValidator, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from typing import List, Literal, TYPE_CHECKING

from bapsf_motion.actors import Axis, Drive, MotionGroup
from bapsf_motion.gui.configure.bases import _ABCMetaQWidget
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.configure.pygame_ import PyGameJoystickRunner
from bapsf_motion.gui.icons import icon_name_dict
from bapsf_motion.gui.widgets import (
    EnableIndicator,
    HLinePlain,
    IconButton,
    LED,
    StyleButton,
    ValidButton,
    ZeroButton,
)
from bapsf_motion.utils import units as u

if TYPE_CHECKING:
    from bapsf_motion.gui.configure.message_boxes import (
        LostConnectionMessageBox,
        MSpaceMessageBox,
    )


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()
    movementStarted = Signal(int)
    movementStopped = Signal(int)
    axisStatusChanged = Signal()
    targetPositionChanged = Signal(float)
    lostConnection = Signal()
    establishedConnection = Signal()
    requestDisplayRefresh = Signal()

    def __init__(
        self,
        axis_display_mode: Literal["interactive", "readonly"] = "interactive",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None
        self._axis_index = None

        # Configure display update timer
        # - to update widgets during a motor movement
        self._update_display_interval = 250  # in msec
        self._update_display_timer = QTimer()
        self._update_display_timer.setSingleShot(True)
        self._display_timer_issue_new_single_shot = False

        # Configure display interactive-ness
        if axis_display_mode not in ("interactive", "readonly"):
            self._logger.info(
                f"Forcing display mode of {self.__class__.__name__} to be"
                f" interactive."
            )
            axis_display_mode = "interactive"
        self._interactive_display_mode = (
            True if axis_display_mode == "interactive" else False
        )

        # Define WIDGETS
        self.axis_name_label = self._init_axis_name_label()
        self.enable_btn = self._init_enable_btn()
        self.encoder_label = self._init_encoder_label()
        self.encoder_label_icon = self._init_encoder_label_icon()
        self.home_btn = self._init_home_btn()
        self.jog_backward_btn = self._init_jog_backward_btn()
        self.jog_delta_label = self._init_jog_delta_label()
        self.jog_forward_btn = self._init_jog_forward_btn()
        self.limit_bwd_btn = self._init_limit_bwd_btn()
        self.limit_fwd_btn = self._init_limit_fwd_btn()
        self.position_label = self._init_position_label()
        self.target_position_label = self._init_target_position_label()
        self.zero_btn = self._init_zero_btn()

        # Retrieve Warning Dialogs from Parent
        self.mspace_warning_dialog = None  # type: MSpaceMessageBox | None
        if hasattr(parent, "mspace_warning_dialog"):
            self.mspace_warning_dialog = parent.mspace_warning_dialog

        self.lost_connection_dialog = None  # type: LostConnectionMessageBox | None
        if hasattr(parent, "lost_connection_dialog"):
            self.lost_connection_dialog = parent.lost_connection_dialog

        self.setFixedWidth(120)
        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        # Note: Connecting/disconnecting of SimpleSignals happens in
        #       the link_axis and unlink_axis methods respectively
        #
        self._update_display_timer.timeout.connect(self._update_display_of_axis_status)

        self.limit_fwd_btn.clicked.connect(self._move_off_limit)
        self.limit_bwd_btn.clicked.connect(self._move_off_limit)

        self.jog_forward_btn.clicked.connect(self.jog_forward)
        self.jog_backward_btn.clicked.connect(self.jog_backward)
        self.zero_btn.clicked.connect(self._zero_axis)
        self.jog_delta_label.editingFinished.connect(self._validate_jog_value)
        self.target_position_label.editingFinished.connect(
            self._validate_target_position_value
        )
        self.enable_btn.clicked.connect(self._set_motor_enabled_state)
        self.movementStopped.connect(self._disable_motor)
        self.movementStopped.connect(self._update_display_of_axis_status)

        self.establishedConnection.connect(self._handle_connection_established)
        self.lostConnection.connect(self._handle_connection_lost)

        self.requestDisplayRefresh.connect(self.update_display_of_axis_status)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if self.interactive_display_mode:
            layout = self._define_interactive_layout(layout)
        else:
            layout = self._define_readonly_layout()

        return layout

    def _define_interactive_layout(self, layout: QVBoxLayout | None = None):
        if layout is None:
            layout = QVBoxLayout()

        layout.addLayout(self._define_title_and_enable_btn_layout())
        layout.addWidget(
            self.position_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addLayout(self._define_encoder_label_layout())
        layout.addWidget(HLinePlain(parent=self))
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

    def _define_readonly_layout(self, layout: QVBoxLayout | None = None):
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

        layout.addLayout(self._define_title_and_enable_btn_layout())
        layout.addSpacing(4)
        layout.addWidget(self.limit_fwd_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addSpacing(8)
        layout.addWidget(
            self.position_label,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addLayout(self._define_encoder_label_layout())
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

    def _define_title_and_enable_btn_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.axis_name_label)
        layout.addSpacing(2)
        layout.addWidget(self.enable_btn)
        layout.addStretch(1)

        return layout

    def _define_encoder_label_layout(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.encoder_label,
            0,
            0,
            5,
            8,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.encoder_label_icon,
            4,
            7,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

        return layout

    def _init_axis_name_label(self):
        _txt = QLabel("Name", parent=self)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setFixedHeight(18)
        return _txt

    def _init_enable_btn(self):
        _btn = EnableIndicator(parent=self)
        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedHeight(24)
        _btn.setFixedWidth(70)
        return _btn

    def _init_encoder_label(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setReadOnly(True)
        _txt.setToolTip(
            "Encoder read position.\n\n If different than motor position, "
            "then the motor is likely slipping / stalling."
        )
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        return _txt

    def _init_encoder_label_icon(self):
        _txt = QLabel("E", parent=self)
        _txt.setObjectName("encoder_icon")
        _txt.setStyleSheet("""
                    QLabel#encoder_icon {
                    color: grey;
                    padding: 2px;
                    }
                    """)
        font = _txt.font()
        font.setPointSize(8)
        font.setBold(True)
        _txt.setFont(font)
        _txt.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        return _txt

    def _init_home_btn(self):
        _btn = StyleButton("HOME", parent=self)
        _btn.setEnabled(False)
        _btn.setVisible(False)
        return _btn

    def _init_jog_backward_btn(self):
        _btn = IconButton(icon_name_dict["arrow-down"], parent=self)
        _btn.setIconSize(42)
        return _btn

    def _init_jog_delta_label(self):
        _txt = QLineEdit("0", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        return _txt

    def _init_jog_forward_btn(self):
        _btn = IconButton(icon_name_dict["arrow-up"], parent=self)
        _btn.setIconSize(42)
        return _btn

    def _init_limit_bwd_btn(self):
        _btn = ValidButton("BWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked",
        )
        return _btn

    def _init_limit_fwd_btn(self):
        _btn = ValidButton("FWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked",
        )
        return _btn

    def _init_position_label(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setReadOnly(True)
        _txt.setToolTip("Motor Position")
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        return _txt

    def _init_target_position_label(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        return _txt

    def _init_zero_btn(self):
        return ZeroButton("ZERO", parent=self)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> MotionGroup | None:
        return self._mg

    @property
    def axis_index(self) -> int:
        return self._axis_index

    @property
    def axis(self) -> Axis | None:
        if (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mg.drive, Drive)
            or self.axis_index is None
        ):
            return None

        axis = self.mg.drive.axes[self.axis_index]
        if not isinstance(axis, Axis):
            return None

        return axis

    @property
    def encoder(self) -> u.Quantity:
        encoder = self.mg.encoder
        val = encoder.value[self.axis_index]
        unit = encoder.unit
        return val * unit

    @property
    def position(self) -> u.Quantity:
        position = self.mg.position
        val = position.value[self.axis_index]
        unit = position.unit
        return val * unit

    @property
    def target_position(self) -> float | int | None:
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

    @Slot()
    def jog_forward(self):
        pos = self.position.value + self._get_jog_delta()
        self._move_to(pos)

    @Slot()
    def jog_backward(self):
        pos = self.position.value - self._get_jog_delta()
        self._move_to(pos)

    def update_encoder_display(self, position: u.Quantity | float | int):
        if not isinstance(position, (u.Quantity, float)):
            return
        elif isinstance(position, u.Quantity):
            _txt = f"{position.value:.2f} {position.unit}"
        else:
            _txt = f"{position:.2f}"

        self.encoder_label.setText(_txt)

    def update_position_display(self, position: u.Quantity | float | int):
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
            _txt = f"{position.value:.2f}"
        else:
            _txt = f"{position:.2f}"

        self.target_position_label.setText(_txt)

    @Slot()
    def _disable_motor(self):
        self.axis.send_command("disable")

    @Slot()
    def _move_off_limit(self):
        axis = self.axis
        if axis is None:
            return

        axis.motor.move_off_limit()

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

    @Slot()
    def _set_motor_enabled_state(self):
        current_enabled_state = self.axis.motor.status["enabled"]
        cmd_string = "disable" if current_enabled_state else "enable"
        self.axis.send_command(cmd_string)

    @Slot()
    def update_display_of_axis_status(self):
        timer_active = self._update_display_timer.isActive()
        if timer_active:
            self._display_timer_issue_new_single_shot = True
        else:
            self._update_display_of_axis_status()

            # start a timed update to start update frequency control
            self._update_display_timer.start(self._update_display_interval)
            self._display_timer_issue_new_single_shot = False

    @Slot()
    def _update_display_of_axis_status(self):
        if self._mg.terminated:
            self.setEnabled(False)
            return

        self.setEnabled(self.axis.connected)
        if not self.isEnabled():
            return

        pos = self.position
        self.update_position_display(pos)
        if self.target_position_label.text() == "":
            self.update_target_position_display(pos)

        encoder = self.encoder
        self.update_encoder_display(encoder)

        if np.isclose(pos.value, encoder.value, rtol=0.0, atol=0.02):
            # encoder and absolute readingss are conssistent
            self.position_label.setStyleSheet("color: black;")
            self.encoder_label.setStyleSheet("color: black;")
        else:
            self.position_label.setStyleSheet("color: red;")
            self.encoder_label.setStyleSheet("color: red;")

        _motor_status = self.axis.motor.status

        limits = _motor_status["limits"]
        self.limit_fwd_btn.set_valid(state=limits["CW"])
        self.limit_bwd_btn.set_valid(state=limits["CCW"])

        enabled_state = _motor_status["enabled"]
        self.enable_btn.setChecked(enabled_state)

        if self._display_timer_issue_new_single_shot:
            # start another single shot if update_display_of_axis_status()
            # was triggered during the wait for the last single shot
            self._update_display_timer.start(self._update_display_interval)
            self._display_timer_issue_new_single_shot = False

    @Slot()
    def _validate_jog_value(self):
        _txt = self.jog_delta_label.text()
        val = 0.0 if _txt == "" else float(_txt)
        val = abs(val)
        self.jog_delta_label.setText(f"{val:.2f}")

    @Slot()
    def _validate_target_position_value(self):
        target_position = self.target_position
        if not isinstance(target_position, float):
            # do nothing, no valid target position
            return
        self.targetPositionChanged.emit(target_position)

    @Slot()
    def _zero_axis(self):
        self.logger.info(f"Setting zero of axis {self.axis_index}")
        self.mg.set_zero(axis=self.axis_index)

    def link_axis(self, mg: MotionGroup | None, ax_index: int):
        if (
            not isinstance(mg, MotionGroup)
            or not isinstance(mg.drive, Drive)
            or not isinstance(ax_index, int)
            or ax_index < 0
            or ax_index >= len(mg.drive.axes)
        ):
            self.unlink_axis()
            return

        axis = mg.drive.axes[ax_index]
        if isinstance(self.axis, Axis) and self.axis is axis:
            pass
        else:
            self.unlink_axis()

        self._mg = mg
        self._axis_index = ax_index

        axis = self.axis
        if not isinstance(axis, Axis):
            self.logger.error("Linking axis failed.")
            return

        self.axis_name_label.setText(axis.name)

        # connect motor SimpleSignals
        axis.motor.signals.connection_established.connect(
            self._emit_connection_established
        )
        axis.motor.signals.connection_lost.connect(self._emit_connection_lost)
        axis.motor.signals.status_changed.connect(self.requestDisplayRefresh.emit)
        axis.motor.signals.status_changed.connect(self.axisStatusChanged.emit)
        axis.motor.signals.movement_started.connect(self._emit_movement_started)
        axis.motor.signals.movement_finished.connect(self._emit_movement_finished)
        axis.motor.signals.movement_finished.connect(self.requestDisplayRefresh.emit)

        self.update_display_of_axis_status()
        self.axisLinked.emit()

    def unlink_axis(self):
        axis = self.axis
        if isinstance(axis, Axis):
            # disconnect all motor SimpleSignals
            axis.motor.signals.connection_established.disconnect(
                self._emit_connection_established
            )
            axis.motor.signals.connection_lost.disconnect(self._emit_connection_lost)
            axis.motor.signals.status_changed.disconnect(self.requestDisplayRefresh.emit)
            axis.motor.signals.status_changed.disconnect(self.axisStatusChanged.emit)
            axis.motor.signals.movement_started.disconnect(self._emit_movement_started)
            axis.motor.signals.movement_finished.disconnect(self._emit_movement_finished)
            axis.motor.signals.movement_finished.disconnect(
                self.requestDisplayRefresh.emit
            )

        self._mg = None
        self._axis_index = None
        self.axisUnlinked.emit()

    @Slot()
    def _emit_connection_established(self):
        self.establishedConnection.emit()

    @Slot()
    def _emit_connection_lost(self):
        self.lostConnection.emit()

    @Slot()
    def _handle_connection_lost(self):
        # Note: This slot needs to be trigger from a PySide6 signal and
        #       not from any of the SimpleSignals attached to Motor.
        #       Having the SimpleSignal execute this code risks the
        #       execution of an unsafe thread operation.  The Motor
        #       event-loop is executing in a different thread that is
        #       unmanaged by PySide6.
        if self.lost_connection_dialog is None:
            return None

        self.lost_connection_dialog.register_lost_motor(
            self.axis.name,
            self.axis.motor.ip,
        )
        self.setEnabled(False)

    @Slot()
    def _handle_connection_established(self):
        # Note: This slot needs to be trigger from a PySide6 signal and
        #       not from any of the SimpleSignals attached to Motor.
        #       Having the SimpleSignal execute this code risks the
        #       execution of an unsafe thread operation.  The Motor
        #       event-loop is executing in a different thread that is
        #       unmanaged by PySide6.
        if self.lost_connection_dialog is None:
            return None

        self.lost_connection_dialog.register_resolved_motor(self.axis.name)

        self.setEnabled(True)
        self.update_display_of_axis_status()
        self.axisStatusChanged.emit()

    @Slot()
    def _emit_movement_started(self):
        self.movementStarted.emit(self.axis_index)

    @Slot()
    def _emit_movement_finished(self):
        self.movementStopped.emit(self.axis_index)

    def enable_motion_buttons(self):
        self.zero_btn.setEnabled(True)
        self.jog_forward_btn.setEnabled(True)
        self.jog_backward_btn.setEnabled(True)
        self.enable_btn.setEnabled(True)

    def disable_motion_buttons(self):
        self.zero_btn.setEnabled(False)
        self.jog_forward_btn.setEnabled(False)
        self.jog_backward_btn.setEnabled(False)
        self.enable_btn.setEnabled(False)

    def closeEvent(self, event: QCloseEvent):
        self.logger.info("Closing AxisControlWidget")

        if isinstance(self.axis, Axis):
            self.axis.motor.signals.connection_established.disconnect(
                self._emit_connection_established
            )
            self.axis.motor.signals.connection_lost.disconnect(self._emit_connection_lost)
            self.axis.motor.signals.status_changed.disconnect(
                self.requestDisplayRefresh.emit
            )
            self.axis.motor.signals.status_changed.disconnect(self.axisStatusChanged.emit)
            self.axis.motor.signals.movement_started.disconnect(
                self._emit_movement_started
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self._emit_movement_finished
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self.requestDisplayRefresh.emit
            )

        event.accept()


class DriveBaseController(QWidget, ABC, metaclass=_ABCMetaQWidget):
    driveStatusChanged = Signal()
    movementStarted = Signal()
    movementStopped = Signal()
    moveTo = Signal(list)
    zeroDrive = Signal()
    targetPositionChanged = Signal(list)

    def __init__(
        self,
        axis_display_mode: Literal["interactive", "readonly"] = "interactive",
        parent: QWidget | None = None,
    ):
        # axis_display_mode == "interactive" or "readonly"
        super().__init__(parent=parent)

        self._logger = gui_logger

        self._axis_display_mode = axis_display_mode
        self.mspace_warning_dialog = None
        if hasattr(parent, "mspace_warning_dialog"):
            self.mspace_warning_dialog = parent.mspace_warning_dialog

        self.lost_connection_dialog = None
        if hasattr(parent, "lost_connection_dialog"):
            self.lost_connection_dialog = parent.lost_connection_dialog

        self._mg = None
        self._mspace_drive_polarity = None

        self._axis_control_widgets = []  # type: List[AxisControlWidget]
        self._initialize_axis_control_widgets()

        self._initialize_widgets()

        self.setLayout(self._define_layout())
        self._connect_signals()

    @abstractmethod
    def _initialize_widgets(self): ...

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
    def _define_layout(self) -> QLayout: ...

    @property
    def logger(self):
        return self._logger

    @property
    def mg(self) -> MotionGroup | None:
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
    def target_position(self) -> List[float] | None:
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

    @Slot(float)
    def _target_position_changed(self, position):
        self.logger.info(f"DBC target position changed {self.target_position}")
        target_position = self.target_position
        if target_position is None:
            target_position = []
        self.targetPositionChanged.emit(target_position)

    def link_motion_group(self, mg: MotionGroup):
        if not isinstance(mg, MotionGroup):
            self.logger.warning(
                f"Expected type {MotionGroup} for motion group, but got type"
                f" {type(mg)}."
            )

        if not isinstance(mg.drive, Drive):
            # drive has not been set yet
            self.unlink_motion_group()
            return

        if (
            isinstance(self.mg, MotionGroup)
            and isinstance(self.mg.drive, Drive)
            and mg.drive is self.mg.drive
        ):
            pass
        else:
            self.unlink_motion_group()
            self._mg = mg

        for ii, ax in enumerate(self.mg.drive.axes):
            acw = self._axis_control_widgets[ii]
            acw.link_axis(self.mg, ii)
            acw.establishedConnection.connect(self._drive_connection_established)
            acw.lostConnection.connect(self._drive_connection_lost)
            acw.movementStarted.connect(self._drive_movement_started)
            acw.movementStopped.connect(self._drive_movement_finished)
            acw.axisStatusChanged.connect(self.update_all_axis_displays)
            acw.axisStatusChanged.connect(self.driveStatusChanged.emit)
            acw.show()

        self.setEnabled(not (self._mg.terminated or not self._mg.connected))
        self._determine_mspace_drive_polarity()

    def unlink_motion_group(self):
        for ii, acw in enumerate(self._axis_control_widgets):
            visible = True if ii == 0 else False

            acw.unlink_axis()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                acw.establishedConnection.disconnect(self._drive_connection_established)
                acw.lostConnection.disconnect(self._drive_connection_lost)
                acw.movementStarted.disconnect(self._drive_movement_started)
                acw.movementStopped.disconnect(self._drive_movement_finished)
                acw.axisStatusChanged.disconnect(self.update_all_axis_displays)
                acw.axisStatusChanged.disconnect(self.driveStatusChanged.emit)

            acw.setVisible(visible)

        # self.mg.terminate(delay_loop_stop=True)
        self._mg = None
        self._mspace_drive_polarity = None
        self.setEnabled(False)

    @Slot()
    def update_all_axis_displays(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            acw.update_display_of_axis_status()

    @Slot()
    def disable_motion_buttons(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            acw.disable_motion_buttons()

    @Slot()
    def enable_motion_buttons(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue

            acw.enable_motion_buttons()

    @Slot()
    def _drive_connection_lost(self):
        self.mg.drive.stop()
        self.setEnabled(False)

    @Slot()
    def _drive_connection_established(self):
        if not isinstance(self.mg, MotionGroup) or not isinstance(self.mg.drive, Drive):
            return

        if self.mg.drive.connected:
            self.setEnabled(True)

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
    def __init__(self, parent: QWidget | None = None):
        super().__init__(axis_display_mode="interactive", parent=parent)

    def _initialize_widgets(self):
        # BUTTON WIDGETS
        _btn = StyleButton("Move \n To", parent=self)
        _btn.setMinimumHeight(100)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        self.move_to_btn = _btn

        _btn = StyleButton("Home \n All", parent=self)
        _btn.setMinimumHeight(100)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.home_btn = _btn
        self.home_btn.setVisible(False)

        _btn = ZeroButton("Zero \n All", parent=self)
        _btn.setMinimumHeight(100)
        _btn.setFont(font)
        self.zero_all_btn = _btn

        _btn = StyleButton("Holding\nCurrent", parent=self)
        _btn.setFixedHeight(44)
        font = _btn.font()
        font.setPointSize(10)
        _btn.setFont(font)
        _btn.update_style_sheet(
            styles={
                "background-color": re.sub(
                    " +",
                    " ",
                    """qlineargradient(
                        x1:0,
                        y1:0, 
                        x2:1, 
                        y2:0,
                        stop: 0 rgb(52, 161, 219),
                        stop: 0.1 rgb(52, 161, 219),
                        stop: 0.4 rgb(163, 163, 163),
                        stop: 1 rgb(163, 163, 163)
                    )""".replace("\n", ""),
                ),
            },
            action="base",
        )
        _btn.update_style_sheet(
            styles={
                "background-color": re.sub(
                    " +",
                    " ",
                    """qlineargradient(
                        x1:0,
                        y1:0, 
                        x2:1, 
                        y2:0,
                        stop: 0 rgb(163, 163, 163),
                        stop: 0.6 rgb(163, 163, 163),
                        stop: 0.9 rgb(250, 66, 45)
                        stop: 1 rgb(250, 66, 45)
                    )""".replace("\n", ""),
                ),
            },
            action="checked",
        )
        _btn.setCheckable(True)
        _btn.setChecked(False)
        self.hold_current_btn = _btn

    def _connect_signals(self):
        super()._connect_signals()

        self.zero_all_btn.clicked.connect(self.zeroDrive.emit)
        self.move_to_btn.clicked.connect(self._move_to)
        self.hold_current_btn.clicked.connect(self._toggle_holding_current)

    def _define_layout(self) -> QLayout:
        _on = QLabel("O\nN", parent=self)
        font = _on.font()
        font.setBold(True)
        _on.setFont(font)
        _on.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _on.setFixedWidth(10)
        _on.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        _off = QLabel("O\nF\nF", parent=self)
        _off.setFont(font)
        _off.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _off.setFixedWidth(10)
        _off.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        holding_current_layout = QHBoxLayout()
        holding_current_layout.setContentsMargins(0, 0, 0, 0)
        holding_current_layout.addWidget(
            _on,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        holding_current_layout.addWidget(self.hold_current_btn)
        holding_current_layout.addWidget(
            _off,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        _on.setVisible(False)
        _off.setVisible(False)
        self.hold_current_btn.setVisible(False)

        # Sub-Layout #1
        sub_layout = QVBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.addWidget(self.move_to_btn)
        sub_layout.addStretch()
        # sub_layout.addWidget(self.home_btn)
        sub_layout.addLayout(holding_current_layout)
        sub_layout.addStretch()
        sub_layout.addWidget(self.zero_all_btn)
        sub_widget = QWidget(parent=self)
        sub_widget.setLayout(sub_layout)
        sub_widget.setFixedWidth(140)

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
        sub_layout2.addSpacing(54)
        sub_layout2.addWidget(
            _pos_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addSpacing(42)
        sub_layout2.addWidget(
            _target_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addSpacing(86)
        sub_layout2.addWidget(
            _jog_delta_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addStretch(1)

        layout = QHBoxLayout()
        layout.addWidget(sub_widget)
        layout.addLayout(sub_layout2)
        for acw in self._axis_control_widgets:
            layout.addWidget(acw)
            layout.addSpacing(2)
        layout.addStretch()

        return layout

    @Slot()
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

    @Slot()
    def _toggle_holding_current(self):
        hold_current = not self.hold_current_btn.isChecked()
        if hold_current:
            self.mg.drive.send_command("reset_currents")
        else:
            idle_currents = [0] * self.mg.drive.naxes
            self.mg.drive.send_command("set_idle_current", *idle_currents)

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
        self.hold_current_btn.setEnabled(False)

        super().disable_motion_buttons()

    def enable_motion_buttons(self):
        self.move_to_btn.setEnabled(True)
        self.zero_all_btn.setEnabled(True)
        self.hold_current_btn.setEnabled(True)

        super().enable_motion_buttons()


class DriveGameController(DriveBaseController):
    def __init__(self, parent=None):
        self._pygame_joystick_runner = None  # type: PyGameJoystickRunner | None

        super().__init__(axis_display_mode="readonly", parent=parent)

    def _connect_signals(self):
        super()._connect_signals()

        self.refresh_controller_list_btn.clicked.connect(self.refresh_controller_combo)
        self.connect_btn.clicked.connect(self.connect_controller)
        self.controller_combo_widget.currentIndexChanged.connect(
            self.disconnect_controller
        )

    def _initialize_widgets(self):
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
    def joystick(self) -> pygame.joystick.JoystickType | None:
        js_name = self.controller_combo_widget.currentText()
        self.logger.info(f"Selected joystick: {js_name} - {self.available_controllers}")
        js = None
        for _js in self.available_controllers:
            if _js.get_name() == js_name:
                js = _js
                break

        return js

    @Slot()
    def refresh_controller_combo(self):
        self.disconnect_controller()

        current_controller_name = self.controller_combo_widget.currentText()

        self.controller_combo_widget.clear()

        controller_names = [
            controller.get_name() for controller in self.available_controllers
        ]
        controller_names.append("")
        self.controller_combo_widget.addItems(controller_names)

        if current_controller_name != "" and current_controller_name in controller_names:
            self.controller_combo_widget.setCurrentText(current_controller_name)
            self.connect_controller()
        else:
            self.controller_combo_widget.setCurrentText("")

    @Slot()
    def connect_controller(self):
        self.logger.info("Connecting controller.")

        if isinstance(self._pygame_joystick_runner, PyGameJoystickRunner):
            self.disconnect_controller()

        selected_joystick = self.joystick
        if not isinstance(selected_joystick, pygame.joystick.JoystickType):
            self.logger.warning("Selected joystick not found.")
            return

        self._pygame_joystick_runner = PyGameJoystickRunner(selected_joystick)

        self._pygame_joystick_runner.signals.joystickConnected.connect(
            self._update_connect_led
        )
        self._pygame_joystick_runner.signals.axisMoved.connect(self._handle_axis_move)
        self._pygame_joystick_runner.signals.buttonPressed.connect(
            self._handle_button_press
        )
        self._pygame_joystick_runner.signals.hatPressed.connect(self._handle_hat_press)
        self._pygame_joystick_runner.signals.stopMovement.connect(self.stop_move)

        self._thread_pool.start(self._pygame_joystick_runner)

    @Slot()
    def disconnect_controller(self):
        if isinstance(self.mg, MotionGroup) and self.mg.is_moving:
            self.stop_move()

        if self._pygame_joystick_runner is None:
            return

        self._pygame_joystick_runner.quit()
        self._pygame_joystick_runner = None
        self._thread_pool.waitForDone(200)
        self._thread_pool.clear()

        if isinstance(self.mg, MotionGroup) and self.mg.is_moving:
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

    @Slot()
    def _drive_connection_lost(self):
        super()._drive_connection_lost()
        self.disconnect_controller()

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

            self.mg.drive.send_command("continuous_jog", direction, axis=axis_id)

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
