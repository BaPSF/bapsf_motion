

import logging
import numpy as np
import warnings

from abc import abstractmethod
from PySide6.QtCore import Signal, QTimer, Qt, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLayout,
)
from typing import List

from bapsf_motion.actors import MotionGroup, Drive, Axis, Motor
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.configure.message_boxes import LostConnectionMessageBox
from bapsf_motion.gui.icons import icon_name_dict
from bapsf_motion.gui.widgets import (
    EnableIndicator,
    IconButton,
    ValidButton,
    StyleButton,
    ZeroButton,
    HLinePlain,
)
from bapsf_motion.utils import units as u


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()
    movementStarted = Signal(int)
    movementStopped = Signal(int)
    axisStatusChanged = Signal()
    targetPositionChanged = Signal(float)
    lostConnection = Signal()
    establishedConnection = Signal()

    def __init__(
        self,
        axis_display_mode="interactive",
        parent=None,
    ):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None
        self._axis_index = None

        self._update_display_interval = 250  # in msec
        self._update_display_timer = QTimer()
        self._update_display_timer.setSingleShot(True)
        self._display_timer_issue_new_single_shot = False

        if axis_display_mode not in ("interactive", "readonly"):
            self._logger.info(
                f"Forcing display mode of {self.__class__.__name__} to be"
                f" interactive."
            )
            axis_display_mode = "interactive"
        self._interactive_display_mode = (
            True if axis_display_mode == "interactive" else False
        )

        self.setFixedWidth(120)

        # Define BUTTONS
        _btn = IconButton(icon_name_dict["arrow-up"], parent=self)
        _btn.setIconSize(42)
        self.jog_forward_btn = _btn

        _btn = IconButton(icon_name_dict["arrow-down"], parent=self)
        _btn.setIconSize(42)
        self.jog_backward_btn = _btn

        _btn = ValidButton("FWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked",
        )
        self.limit_fwd_btn = _btn

        _btn = ValidButton("BWD LIMIT", parent=self)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked",
        )
        self.limit_bwd_btn = _btn

        _btn = StyleButton("HOME", parent=self)
        _btn.setEnabled(False)
        self.home_btn = _btn
        self.home_btn.setHidden(True)

        _btn = ZeroButton("ZERO", parent=self)
        self.zero_btn = _btn

        _btn = EnableIndicator(parent=self)
        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedHeight(24)
        _btn.setFixedWidth(70)
        self.enable_btn = _btn

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
        _txt.setToolTip("Motor Position")
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        self.position_label = _txt

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
        self.encoder_label = _txt

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
        self.encoder_label_icon = _txt

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

        self.lost_connection_dialog = None  # type: LostConnectionMessageBox | None
        if hasattr(parent, "lost_connection_dialog"):
            self.lost_connection_dialog = parent.lost_connection_dialog

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
        if self.mg is None or self.axis_index is None:
            return None

        return self.mg.drive.axes[self.axis_index]

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
        self.targetPositionChanged.emit(self.target_position)

    @Slot()
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

        # connect motor SimpleSignals
        self.axis.motor.signals.connection_established.connect(
            self._emit_connection_established
        )
        self.axis.motor.signals.connection_lost.connect(self._emit_connection_lost)
        self.axis.motor.signals.status_changed.connect(self.update_display_of_axis_status)
        self.axis.motor.signals.status_changed.connect(self.axisStatusChanged.emit)
        self.axis.motor.signals.movement_started.connect(self._emit_movement_started)
        self.axis.motor.signals.movement_finished.connect(self._emit_movement_finished)
        self.axis.motor.signals.movement_finished.connect(
            self.update_display_of_axis_status
        )

        self.update_display_of_axis_status()
        self.axisLinked.emit()

    def unlink_axis(self):
        if self.axis is not None:
            # disconnect all motor SimpleSignals
            self.axis.motor.signals.connection_established.disconnect(
                self._emit_connection_established
            )
            self.axis.motor.signals.connection_lost.disconnect(self._emit_connection_lost)
            self.axis.motor.signals.status_changed.disconnect(
                self.update_display_of_axis_status
            )
            self.axis.motor.signals.status_changed.disconnect(self.axisStatusChanged.emit)
            self.axis.motor.signals.movement_started.disconnect(
                self._emit_movement_started
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self._emit_movement_finished
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self.update_display_of_axis_status
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

    def closeEvent(self, event):
        self.logger.info("Closing AxisControlWidget")

        if isinstance(self.axis, Axis):
            self.axis.motor.signals.connection_established.disconnect(
                self._emit_connection_established
            )
            self.axis.motor.signals.connection_lost.disconnect(self._emit_connection_lost)
            self.axis.motor.signals.status_changed.disconnect(
                self.update_display_of_axis_status
            )
            self.axis.motor.signals.status_changed.disconnect(self.axisStatusChanged.emit)
            self.axis.motor.signals.movement_started.disconnect(
                self._emit_movement_started
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self._emit_movement_finished
            )
            self.axis.motor.signals.movement_finished.disconnect(
                self.update_display_of_axis_status
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

    @Slot()
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
            # elif acw.axis.is_moving:
            #     continue

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
