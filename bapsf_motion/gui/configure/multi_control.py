from __future__ import annotations

__all__ = ["MultiControl"]

import logging
import numpy as np
import re

from PySide6.QtCore import QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QDoubleValidator, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from typing import List, TYPE_CHECKING

from bapsf_motion.actors import Axis, MotionGroup, RunManager
from bapsf_motion.gui.configure.bases import _OverlayWidget
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.configure.toml_ import TOMLText
from bapsf_motion.gui.icons import icon_name_dict
from bapsf_motion.gui.widgets import (
    DoneButton,
    EnableIndicator,
    HLinePlain,
    IconButton,
    QVerticalLabel,
    StopButton,
    StyleButton,
    ValidButton,
    VLinePlain,
)
from bapsf_motion.utils import SimpleSignal
from bapsf_motion.utils import units as u

# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta  # noqa

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from bapsf_motion.gui.configure.configure_ import ConfigureGUI, RMObject


class MGDetailsOverlay(_OverlayWidget):
    def __init__(self, *, mg: MotionGroup, parent: QWidget | None):
        super().__init__(parent=parent)
        self._mg = mg

        base_logger = gui_logger if not hasattr(parent, "logger") else parent.logger
        self._logger = logging.getLogger(f"{base_logger.name}.MGDO")

        # instantiate widgets
        self.config_btn = self._init_config_btn()
        self.done_btn = self._init_done_btn()
        self.toml_widget = self._init_toml_widget()

        self.toml_widget.setPlainText(mg.config.as_toml_string)

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.done_btn.clicked.connect(self.close)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)
        layout.addWidget(self.toml_widget, stretch=1)
        layout.addSpacing(12)
        layout.addLayout(self._define_layout_btn_row())
        return layout

    def _define_layout_btn_row(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        layout.addWidget(self.config_btn)
        layout.addSpacing(12)
        layout.addWidget(self.done_btn)
        layout.addStretch(1)
        return layout

    def _init_config_btn(self):
        btn = StyleButton("Configure", parent=self)
        font = btn.font()
        font.setPixelSize(18)
        btn.setFont(font)
        btn.setFixedHeight(36)
        btn.setMinimumWidth(12 * 12)
        btn.setEnabled(False)
        return btn

    def _init_done_btn(self):
        btn = DoneButton("CLOSE", parent=self)
        font = btn.font()
        font.setPixelSize(18)
        btn.setFont(font)
        btn.setFixedHeight(36)
        return btn

    def _init_toml_widget(self):
        _widget = TOMLText(parent=self)
        _widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        _widget.setMinimumWidth(350)
        return _widget

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def closeEvent(self, event: QCloseEvent):
        self.logger.info(f"Closing {self.__class__.__name__}")

        self._mg = None
        super().closeEvent(event)


class MGControlAxis(QWidget):
    axisStatusChanged = Signal()

    movementStarted = Signal(int)
    movementStopped = Signal(int)

    lostConnection = Signal()
    establishedConnection = Signal()

    refreshDisplay = Signal()

    _actorStatusChanged = Signal()

    def __init__(
        self,
        *,
        rmo: RMObject,
        mg_id: str | int,
        ax_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        base_logger = gui_logger if not hasattr(parent, "logger") else parent.logger
        self._logger = logging.getLogger(f"{base_logger.name}.MGCA")

        self._rmo = rmo
        self._mg_id = mg_id
        self._mg = self._rmo.rm.mgs[mg_id]
        self._ax_id = ax_id
        self._axis = self._mg.drive.axes[ax_id]

        self._motor_signal_mapping = {
            "connection_established": [self._actor_slot_connection_established],
            "connection_lost": [self._actor_slot_connection_lost],
            "status_changed": [self._actor_slot_status_changed],
            "movement_started": [self._actor_slot_movement_started],
            "movement_finished": [self._actor_slot_movement_finished],
        }

        # Configure display update timer
        # - to update widgets during a motor movement
        self._update_display_interval = 250  # in msec
        self._update_display_timer = QTimer()
        self._update_display_timer.setSingleShot(True)
        self._display_timer_issue_new_single_shot = False

        # Initialize Widgets
        self.axis_name_label = self._init_axis_name_label(self._axis.name)
        self.connected_ind = self._init_connected_ind()
        self.enable_btn = self._init_enable_btn()
        self.encoder_ind = self._init_encoder_ind()
        self.encoder_ind_icon = self._init_encoder_ind_icon()
        self.indicator_column_widget = self._init_indicator_column_widget()
        self.jog_backward_btn = self._init_jog_backward_btn()
        self.jog_delta_input = self._init_jog_delta_input()
        self.jog_delta_icon = self._init_jog_delta_icon()
        self.jog_forward_btn = self._init_jog_forward_btn()
        self.limit_bwd_btn = self._init_limit_bwd_btn()
        self.limit_fwd_btn = self._init_limit_fwd_btn()
        self.mg_details_btn = None
        self.movement_column_widget = self._init_movement_column_widget()
        self.position_ind = self._init_position_ind()
        self.position_ind_icon = self._init_position_ind_icon()

        self.setLayout(self._define_layout())
        self._connect_signals()

        self.motor_signals_connect()
        self.refreshDisplay.emit()

    def _connect_signals(self):
        self._update_display_timer.timeout.connect(self._update_displays)

        self.limit_fwd_btn.clicked.connect(self._move_off_limit)
        self.limit_bwd_btn.clicked.connect(self._move_off_limit)

        self.jog_forward_btn.clicked.connect(self.jog_forward)
        self.jog_backward_btn.clicked.connect(self.jog_backward)
        self.jog_delta_input.editingFinished.connect(self._validate_jog_delta_input)
        self.enable_btn.clicked.connect(self._set_motor_enabled_state)

        self._actorStatusChanged.connect(self._handle_actor_status_changed)
        self.movementStopped.connect(self._handle_movement_stopped)
        self.establishedConnection.connect(self._handle_connection_established)
        self.lostConnection.connect(self._handle_connection_lost)

        self.refreshDisplay.connect(self.update_displays)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._define_layout_header())
        layout.addSpacing(8)
        layout.addLayout(self._define_layout_control_area())
        return layout

    def _define_layout_header(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.axis_name_label)
        layout.addStretch(1)
        layout.addWidget(self.connected_ind)
        layout.addStretch(1)
        return layout

    def _define_layout_control_area(self):
        self.indicator_column_widget.setLayout(self._define_layout_indicator_column())
        self.movement_column_widget.setLayout(self._define_layout_movement_column())

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.indicator_column_widget)
        layout.addSpacing(8)
        layout.addWidget(self.movement_column_widget)
        return layout

    def _define_layout_indicator_column(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._define_layout_enable_btn())
        layout.addSpacing(4)
        layout.addLayout(self._define_layout_position_ind())
        layout.addSpacing(4)
        layout.addLayout(self._define_layout_encoder_ind())
        layout.addStretch(1)
        layout.addLayout(self._define_layout_jog_delta_input())
        return layout

    def _define_layout_movement_column(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.limit_fwd_btn)
        layout.addWidget(self.jog_forward_btn, stretch=1)
        layout.addWidget(self.jog_backward_btn, stretch=1)
        layout.addWidget(self.limit_bwd_btn)
        return layout

    def _define_layout_enable_btn(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(self.enable_btn)
        layout.addStretch(1)
        return layout

    def _define_layout_encoder_ind(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.encoder_ind,
            0,
            0,
            5,
            8,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.encoder_ind_icon,
            4,
            7,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

        return layout

    def _define_layout_jog_delta_input(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.jog_delta_input,
            0,
            0,
            5,
            8,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.jog_delta_icon,
            4,
            7,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

        return layout

    def _define_layout_position_ind(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.position_ind,
            0,
            0,
            5,
            8,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.position_ind_icon,
            4,
            7,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )

        return layout

    def _init_axis_name_label(self, name: str):
        _txt = QLabel(name, parent=self)
        font = _txt.font()
        font.setPointSize(14)
        font.setBold(True)
        _txt.setFont(font)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setFixedHeight(18)
        return _txt

    def _init_connected_ind(self):
        _btn = EnableIndicator(parent=self)
        _btn._enabled_text = self.axis.ip
        _btn._disabled_text = self.axis.ip
        _btn.setChecked(False)
        _btn.update_style_sheet(
            styles={"background-color": "rgb(129, 201, 149)"},
            action="checked",
        )  # when checked set color to green
        _btn.update_style_sheet(
            styles={"border": _btn.base_style["border"]},
            action="hover",
        )  # removing the border highlighting during hover

        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedHeight(24)
        _btn.setFixedWidth(120)
        return _btn

    def _init_enable_btn(self):
        _btn = EnableIndicator(parent=self)
        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedHeight(24)
        _btn.setFixedWidth(70)
        return _btn

    def _init_encoder_ind(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        _txt.setReadOnly(True)
        _txt.setToolTip(
            "Encoder read position.\n\n If different than motor position, "
            "then the motor is likely slipping / stalling."
        )
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setFixedHeight(30)
        return _txt

    def _init_encoder_ind_icon(self):
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

    def _init_indicator_column_widget(self):
        _w = QWidget(parent=self)
        _w.setFixedWidth(10 * 12)
        return _w

    def _init_jog_backward_btn(self):
        _btn = IconButton(icon_name_dict["arrow-down"], parent=self)
        _btn.setIconSize(42)
        return _btn

    def _init_jog_delta_icon(self):
        _txt = QLabel("JOG Δ", parent=self)
        _txt.setObjectName("jog_icon")
        _txt.setStyleSheet("""
        QLabel#jog_icon {
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

    def _init_jog_delta_input(self):
        _txt = QLineEdit(f"{1.0:.2f}", parent=self)
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

    def _init_movement_column_widget(self):
        _w = QWidget(parent=self)
        _w.setFixedWidth(7 * 12)
        return _w

    def _init_position_ind(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        _txt.setReadOnly(True)
        _txt.setToolTip("Motor Position")
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setFixedHeight(30)
        return _txt

    def _init_position_ind_icon(self):
        _txt = QLabel("P", parent=self)
        _txt.setObjectName("position_icon")
        _txt.setStyleSheet("""
        QLabel#position_icon {
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

    @property
    def axis(self) -> Axis:
        return self._axis

    @property
    def axis_id(self) -> int:
        return self._ax_id

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> MotionGroup:
        return self._mg

    @property
    def encoder(self) -> u.Quantity:
        encoder = self.mg.encoder
        val = encoder.value[self.axis_id]
        unit = encoder.unit
        return val * unit

    @property
    def position(self) -> u.Quantity:
        position = self.mg.position
        val = position.value[self.axis_id]
        unit = position.unit
        return val * unit

    def _actor_slot_connection_established(self):
        self.establishedConnection.emit()

    def _actor_slot_connection_lost(self):
        self.lostConnection.emit()

    def _actor_slot_movement_started(self):
        self.movementStarted.emit(self._ax_id)

    def _actor_slot_movement_finished(self):
        self.movementStopped.emit(self._ax_id)

    def _actor_slot_status_changed(self):
        self._actorStatusChanged.emit()

    def _get_jog_delta(self):
        delta_str = self.jog_delta_input.text()
        return float(delta_str)

    def _move_to(self, target_ax_pos):
        target_pos = self.mg.position.value
        target_pos[self.axis_id] = target_ax_pos

        if self.mg.drive.is_moving:
            self.logger.info(
                "Probe drive is currently moving.  Did NOT perform move "
                f"to {target_pos}."
            )
            return

        self.mg.move_to(target_pos)

    def motor_signals_connect(self):
        axis = self.axis
        if not isinstance(axis, Axis):
            return

        for motor_signal, callbacks in self._motor_signal_mapping.items():
            signal = getattr(axis.motor.signals, motor_signal, None)

            if not isinstance(signal, SimpleSignal):
                continue

            for callback in callbacks:
                signal.connect(callback)

    def motor_signals_disconnect(self):
        axis = self.axis
        if not isinstance(axis, Axis):
            return

        axis.motor.signals.set_blocking(True)
        axis.motor.signals.disconnect_all()

    def motor_signals_set_blocking(self, block: bool):
        if not isinstance(block, bool):
            return

        axis = self.axis
        if not isinstance(axis, Axis):
            return

        for motor_signal in self._motor_signal_mapping.keys():
            signal = getattr(axis.motor.signals, motor_signal, None)

            if not isinstance(signal, SimpleSignal):
                continue

            signal.set_blocking(block)

    def update_display_connected(self):
        is_connected = self.axis.connected
        self.connected_ind.setChecked(is_connected)

    def update_display_encoder(self, position: u.Quantity | float | int):
        if not isinstance(position, (u.Quantity, float)):
            return
        elif isinstance(position, u.Quantity):
            _txt = f"{position.value:.2f} {position.unit}"
        else:
            _txt = f"{position:.2f}"

        self.encoder_ind.setText(_txt)

    def update_display_position(self, position: u.Quantity | float | int):
        if not isinstance(position, (u.Quantity, float)):
            return
        elif isinstance(position, u.Quantity):
            _txt = f"{position.value:.2f} {position.unit}"
        else:
            _txt = f"{position:.2f}"

        self.position_ind.setText(_txt)

    @Slot()
    def jog_forward(self):
        pos = self.position.value + self._get_jog_delta()
        self._move_to(pos)

    @Slot()
    def jog_backward(self):
        pos = self.position.value - self._get_jog_delta()
        self._move_to(pos)

    @Slot()
    def update_displays(self):
        timer_active = self._update_display_timer.isActive()
        if timer_active:
            self._display_timer_issue_new_single_shot = True
        else:
            self._update_displays()

            # start a timed update to start update frequency control
            self._update_display_timer.start(self._update_display_interval)
            self._display_timer_issue_new_single_shot = False

    @Slot()
    def _update_displays(self):
        if self._mg.terminated:
            self.setEnabled(False)
            self.connected_ind.setChecked(False)
            return

        self.update_display_connected()

        connected = self.axis.connected
        self.setEnabled(connected)
        if not connected:
            return

        _motor_status = self.axis.motor.status

        limits = _motor_status["limits"]
        self.limit_fwd_btn.set_valid(state=limits["CW"])
        self.limit_bwd_btn.set_valid(state=limits["CCW"])

        enabled_state = _motor_status["enabled"]
        self.enable_btn.setChecked(enabled_state)

        # do not update position / encoder displays if the whole motion
        # group is not connected
        if not self.mg.connected:
            return

        pos = self.position
        self.update_display_position(pos)

        encoder = self.encoder
        self.update_display_encoder(encoder)

        if np.isclose(pos.value, encoder.value, rtol=0.0, atol=0.02):
            # encoder and absolute readingss are conssistent
            self.position_ind.setStyleSheet("color: black;")
            self.encoder_ind.setStyleSheet("color: black;")
        else:
            self.position_ind.setStyleSheet("color: red;")
            self.encoder_ind.setStyleSheet("color: red;")

        if self._display_timer_issue_new_single_shot:
            # start another single shot if update_displays()
            # was triggered during the wait for the last single shot
            self._update_display_timer.start(self._update_display_interval)
            self._display_timer_issue_new_single_shot = False

    @Slot()
    def _handle_actor_status_changed(self):
        self.update_displays()
        self.axisStatusChanged.emit()

    @Slot()
    def _handle_connection_established(self):
        # Note: This slot needs to be trigger from a PySide6 signal and
        #       not from any of the SimpleSignals attached to Motor.
        #       Having the SimpleSignal execute this code risks the
        #       execution of an unsafe thread operation.  The Motor
        #       event-loop is executing in a different thread that is
        #       unmanaged by PySide6.
        self.setEnabled(True)
        self.update_displays()
        self.axisStatusChanged.emit()

    @Slot()
    def _handle_connection_lost(self):
        # Note: This slot needs to be trigger from a PySide6 signal and
        #       not from any of the SimpleSignals attached to Motor.
        #       Having the SimpleSignal execute this code risks the
        #       execution of an unsafe thread operation.  The Motor
        #       event-loop is executing in a different thread that is
        #       unmanaged by PySide6.
        self.setEnabled(False)
        for ax in self.mg.drive.axes:
            if ax.connected:
                ax.stop()

    @Slot()
    def _handle_movement_stopped(self):
        self.axis.send_command("disable")
        self.update_displays()
        self.axisStatusChanged.emit()

    @Slot()
    def _move_off_limit(self):
        axis = self.axis
        if not isinstance(axis, Axis):
            return

        axis.motor.move_off_limit()

    @Slot()
    def _set_motor_enabled_state(self):
        current_enabled_state = self.axis.motor.status["enabled"]
        cmd_string = "disable" if current_enabled_state else "enable"
        self.axis.send_command(cmd_string)

    @Slot()
    def _validate_jog_delta_input(self):
        _txt = self.jog_delta_input.text()
        val = 0.0 if _txt == "" else float(_txt)
        val = abs(val)
        self.jog_delta_input.setText(f"{val:.2f}")

    def set_enabled_for_movement(self, state: bool):
        if not isinstance(state, bool):
            return

        self.enable_btn.setEnabled(state)
        self.jog_backward_btn.setEnabled(state)
        self.jog_forward_btn.setEnabled(state)
        self.limit_bwd_btn.setEnabled(state)
        self.limit_fwd_btn.setEnabled(state)

    def closeEvent(self, event: QCloseEvent):
        self.logger.info(
            f"Closing {self.__class__.__name__} ({self._mg_id}-{self._ax_id})"
        )

        self.motor_signals_disconnect()
        self._update_display_timer.stop()
        self.jog_delta_input.blockSignals(True)

        self._axis = None
        self._mg = None
        self._rmo = None

        super().closeEvent(event)


class MGControl(QWidget):
    movementStarted = Signal()
    movementStopped = Signal()
    requestDetailPopUp = Signal(str)

    def __init__(self, *, rmo: RMObject, motion_group_id: str | int, parent: QWidget):
        super().__init__(parent)
        self._rmo = rmo
        self._mg_id = motion_group_id
        self._mg = self._rmo.rm.mgs[motion_group_id]

        base_logger = gui_logger if not hasattr(parent, "logger") else parent.logger
        self._logger = logging.getLogger(f"{base_logger.name}.MGC")

        # initialize widgets
        self.details_btn = self._init_details_btn()
        self.drive_name_label = self._init_drive_name_label()
        self.move_to_btn = self._init_move_to_btn()
        self.terminate_run_btn = self._init_terminate_run_btn()

        # initialize "lists" of widgets
        self.axis_target_position_input = []  # type: List[QLineEdit]
        self.axis_target_position_label = []  # type: List[QLabel]
        self.axis_control_widgets = []  # type: List[MGControlAxis]
        for ax_id in range(len(self._mg.drive.axes)):
            ax_tp_input = self._init_target_position_input()
            self.axis_target_position_input.append(ax_tp_input)

            axis = self._mg.drive.axes[ax_id]
            ax_tp_label = self._init_target_position_label(axis.name)
            self.axis_target_position_label.append(ax_tp_label)

            ax_control = MGControlAxis(
                rmo=self._rmo,
                mg_id=self._mg_id,
                ax_id=ax_id,
                parent=self,
            )
            ax_control.movementStarted.connect(self._handle_movement_started)
            ax_control.movementStopped.connect(self._handle_movement_stopped)
            ax_control.lostConnection.connect(self._handle_connection_lost)
            ax_control.establishedConnection.connect(self._handle_connection_established)
            self.axis_control_widgets.append(ax_control)

        # initialize "complex" widgets
        # - These widgets require the "base" widgets to be defined first
        self.move_to_widget = self._init_move_to_widget()

        self.setLayout(self._define_layout())
        self.setFixedHeight(int(14 * 12))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._connect_signals()

        self.update_display_target_position()

    def _connect_signals(self):
        self.details_btn.clicked.connect(self._handle_details_btn_clicked)
        self.move_to_btn.clicked.connect(self._move_to)
        self.terminate_run_btn.clicked.connect(self._handle_terminate_run_clicked)

        for input_ in self.axis_target_position_input:
            input_.editingFinished.connect(self.update_display_target_position)

    def _define_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addLayout(self._define_layout_drive_name())
        layout.addLayout(self._define_layout_vdivider())
        layout.addSpacing(8)
        layout.addWidget(self.move_to_widget)

        for ax_widget in self.axis_control_widgets:
            layout.addSpacing(8)
            layout.addLayout(self._define_layout_vdivider())
            layout.addSpacing(8)
            layout.addWidget(ax_widget)

        layout.addSpacing(8)
        layout.addLayout(self._define_layout_vdivider())
        layout.addStretch(1)
        layout.addWidget(self.details_btn)
        layout.addSpacing(8)
        layout.addWidget(self.terminate_run_btn)
        return layout

    def _define_layout_drive_name(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)
        layout.addWidget(
            self.drive_name_label,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch(1)
        return layout

    def _define_layout_vdivider(self):
        divider = VLinePlain(parent=self)
        divider.set_color(60, 60, 60)
        divider.setLineWidth(2)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(8)
        layout.addWidget(divider)
        layout.addSpacing(8)
        return layout

    def _define_layout_move_to_widget(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.move_to_btn)
        layout.addStretch(1)

        for label, input_ in zip(
            self.axis_target_position_label, self.axis_target_position_input
        ):
            layout.addSpacing(3)
            layout.addLayout(self._define_layout_target_position_row(label, input_))
            layout.addSpacing(3)

        layout.addStretch(1)
        return layout

    @staticmethod
    def _define_layout_target_position_row(label: QLabel, input_: QLineEdit):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(label)
        layout.addSpacing(10)
        layout.addWidget(input_, stretch=1)
        return layout

    def _init_details_btn(self):
        _btn = StyleButton("\n".join("DETAILS"), parent=self)

        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedWidth(28)
        _btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        _btn.update_style_sheet(
            styles={},
            action="base",
            reset=True,
        )

        return _btn

    def _init_drive_name_label(self):
        label = QVerticalLabel(self.mg.drive.name, parent=self)
        label.setObjectName("drive_label")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        font = label.font()
        font.setPixelSize(24)
        font.setBold(True)
        label.setFont(font)
        label.setFixedWidth(32)
        return label

    def _init_move_to_btn(self):
        _btn = StyleButton("Move To", parent=self)
        _btn.setFixedHeight(4 * 12)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        return _btn

    def _init_move_to_widget(self):
        w = QWidget(parent=self)
        w.setLayout(self._define_layout_move_to_widget())
        w.setFixedWidth(14 * 12)
        return w

    def _init_target_position_input(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        _txt.setReadOnly(False)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setFixedHeight(30)
        return _txt

    def _init_target_position_label(self, name: str):
        _txt = QLabel(name, parent=self)
        font = _txt.font()
        font.setPointSize(14)
        font.setBold(True)
        _txt.setFont(font)
        _txt.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _txt.setFixedHeight(18)
        return _txt

    def _init_terminate_run_btn(self):
        _btn = EnableIndicator(parent=self)
        _btn._enabled_text = "\n".join("RUN")
        _btn._disabled_text = "\n".join("TERMINATE")
        _btn.setChecked(False)

        font = self.font()
        font.setPointSize(8)
        font.setBold(True)
        _btn.setFont(font)
        _btn.setFixedWidth(28)
        _btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        _btn.update_style_sheet(
            styles={},
            action="base",
            reset=True,
        )

        _btn.setEnabled(False)
        return _btn

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> MotionGroup:
        return self._mg

    @property
    def encoder(self) -> list:
        encoder = self.mg.encoder.value  # type: np.ndarray
        return encoder.tolist()

    @property
    def position(self) -> list:
        pos = self.mg.position.value  # type: np.ndarray
        return pos.tolist()

    @property
    def target_position(self) -> list:
        position = self.position
        target_position = []
        for ax_id, input_ in enumerate(self.axis_target_position_input):
            try:
                tp = float(input_.text())
            except ValueError:
                tp = position[ax_id]

            target_position.append(tp)

        return target_position

    @Slot()
    def update_display_target_position(self):
        position = self.target_position
        for value, input_ in zip(position, self.axis_target_position_input):
            input_.setText(f"{value:.2f}")

    @Slot()
    def _move_to(self):
        target_position = self.target_position
        self.mg.move_to(target_position)

    @Slot()
    def _handle_connection_lost(self):
        self.set_enabled_for_movement(False)
        self.terminate_run_btn.setEnabled(True)

    @Slot()
    def _handle_connection_established(self):
        if not self.mg.connected:
            return

        self.set_enabled_for_movement(True)
        self.terminate_run_btn.setEnabled(False)

        for ax_control in self.axis_control_widgets:
            if not ax_control.isEnabled():
                ax_control.establishedConnection.emit()

    @Slot()
    def _handle_details_btn_clicked(self):
        self.requestDetailPopUp.emit(str(self._mg_id))

    @Slot()
    def _handle_movement_started(self):
        self.set_enabled_for_movement(False)
        self.movementStarted.emit()

    @Slot()
    def _handle_movement_stopped(self):
        if self.mg.is_moving:
            return

        self.set_enabled_for_movement(True)
        self.movementStopped.emit()

    @Slot()
    def _handle_terminate_run_clicked(self):
        state = self.terminate_run_btn.isChecked()

        if not state:
            # checked state is false and a motion group termination is requested
            self.mg.terminate(delay_loop_stop=True, disconnect_signals=False)
            self.terminate_run_btn.setChecked(True)
            return

        # check state is true and a motion group run is requested
        self.mg.run()
        self.terminate_run_btn.setChecked(False)

        # setup timer to check if motors are reconnected
        _timer = QTimer(parent=self)
        _timer.setSingleShot(True)
        _timer.setInterval(100)
        _timer.timeout.connect(self._handle_connection_established)
        _timer.start()

    def set_enabled_for_movement(self, state: bool):
        if not isinstance(state, bool):
            return

        self.move_to_btn.setEnabled(state)
        self.details_btn.setEnabled(state)
        for ax_control in self.axis_control_widgets:
            ax_control.set_enabled_for_movement(state)

    def closeEvent(self, event: QCloseEvent):
        self.logger.info(f"Closing {self.__class__.__name__} ({self._mg_id})")

        for input_ in self.axis_target_position_input:
            # Closing MGControl causes an axis_target_position_input to lose
            # focus (if the cursor was in the line edit), and thus triggering
            # and editingFinsihed signal and update_target_position().  This
            # results in an AttributeError since _mg is set to None (below)
            # before slot does its routine.
            #
            input_.blockSignals(True)

        # stop movement
        self.mg.stop()

        # TODO: create a dialog to display waiting for motion to stop

        # Explicitly close MGControlAxis widgets
        for ax_control in self.axis_control_widgets:
            ax_control.close()

        self._mg = None
        self._rmo = None

        super().closeEvent(event)


class MultiControl(QWidget):
    closing = Signal()
    returnConfig = Signal(int, object)

    def __init__(self, *, rmo: RMObject, parent: ConfigureGUI):
        super().__init__(parent)
        self._rmo = rmo
        self._configure_gui = parent

        # Initialize Attributes
        self._logger = logging.getLogger(f"{gui_logger.name}.MC")

        # Initialize Widgets
        self.return_btn = self._init_return_btn()
        self.stop_btn = self._init_stop_btn()
        self.mg_control_widgets = {}
        self._overlay_widget = None  # type: MGDetailsOverlay | None

        # Setup Self
        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.return_btn.clicked.connect(self.close)
        self.stop_btn.clicked.connect(self.stop_all)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._define_banner_layout())
        layout.addSpacing(8)
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(8)
        layout.addWidget(self.stop_btn)

        for mg_id, mg in self.rm.mgs.items():
            if mg.terminated or not mg.connected:
                continue

            _widget = self._spawn_mg_control_widget(mg_id)

            layout.addSpacing(8)
            layout.addWidget(_widget)

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
        btn.setFixedHeight(8 * 12)

        font = btn.font()
        font.setPixelSize(32)
        font.setBold(True)
        btn.setFont(font)

        return btn

    @Slot()
    def _overlay_close(self):
        overlay = self._overlay_widget
        if not isinstance(overlay, MGDetailsOverlay):
            return

        overlay.deleteLater()
        self._overlay_widget = None
        self._overlay_shown = False

    def _overlay_setup(self):
        overlay = self._overlay_widget
        if not isinstance(overlay, MGDetailsOverlay):
            return

        overlay.move(0, 0)
        overlay._margins = [0.2, 0.05]
        overlay._set_contents_margins(0.2, 0.05)
        overlay.resize(self.width(), self.height())
        overlay.closing.connect(self._overlay_close)

    def _spawn_details_popup(self, mg: MotionGroup):
        self._overlay_widget = MGDetailsOverlay(
            mg=mg,
            parent=self,
        )
        self._overlay_setup()
        self._overlay_widget.show()
        self._overlay_shown = True

    def _spawn_mg_control_widget(self, mg_id):
        _widget = MGControl(
            rmo=self.rmo,
            motion_group_id=mg_id,
            parent=self,
        )
        _widget.movementStarted.connect(self._handle_movement_started)
        _widget.movementStopped.connect(self._handle_movement_stopped)
        _widget.requestDetailPopUp.connect(self._handle_request_details_popup)
        self.mg_control_widgets[mg_id] = _widget

        _frame_layout = QVBoxLayout()
        _frame_layout.setContentsMargins(0, 0, 0, 0)
        _frame_layout.setSpacing(0)
        _frame_layout.addWidget(_widget)

        _frame = QFrame(parent=self)
        _frame.setObjectName("mgc_frame")
        _frame.setLayout(_frame_layout)
        _frame.setStyleSheet("""
        QFrame#mgc_frame {
            border: 2px solid rgb(60, 60, 60);
            border-radius: 5px;
            padding: 6px;
            margin: 0px;
        }
        """)

        return _frame

    @Slot()
    def _handle_movement_started(self):
        self.set_enabled_for_movement(False)

    @Slot()
    def _handle_movement_stopped(self):
        if self.rm.is_moving:
            return

        self.set_enabled_for_movement(True)

    @Slot(str)
    def _handle_request_details_popup(self, mg_id: str):
        rm = self.rm
        if not isinstance(rm, RunManager):
            return

        if rm.is_moving:
            self.stop_all()

        # retrieve the motion group that requestDetailsPopUp requested
        try:
            mg = rm.mgs[mg_id]
        except KeyError:
            # mg_id not found in mgs, try converting mg_id to an int
            try:
                mg_id = int(mg_id)
            except ValueError:
                return

            try:
                mg = rm.mgs[mg_id]
            except KeyError:
                # mg_id not found in mgs
                return

        self._spawn_details_popup(mg)

    @Slot()
    def stop_all(self):
        for mg in self.rm.mgs.values():
            mg.stop()

    def set_enabled_for_movement(self, state: bool):
        if not isinstance(state, bool):
            return

        self.return_btn.setEnabled(state)

    def closeEvent(self, event: QCloseEvent):
        self.logger.info(f"Closing {self.__class__.__name__}")

        # stop any moving motor
        rm = self.rmo.rm
        if isinstance(rm, RunManager) and rm.is_moving:
            for mg in rm.mgs.values():
                mg.stop()

            # TODO: create a dialog to display waiting for motion to stop

        self._rmo = None

        # Explicitly close overlay
        overlay = self._overlay_widget
        if isinstance(overlay, MGDetailsOverlay):
            overlay.close()

        # Explicitly close the MGControl widgets
        for mg_control in self.mg_control_widgets.values():
            mg_control.close()

        self.closing.emit()
        super().closeEvent(event)
