from __future__ import annotations

__all__ = ["MultiControl"]

import logging
import re

from PySide6.QtCore import QSize, Qt, Signal, Slot
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
from typing import TYPE_CHECKING

from bapsf_motion.actors import Axis, MotionGroup, RunManager
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.icons import icon_name_dict
from bapsf_motion.gui.widgets import (
    DoneButton,
    EnableIndicator,
    HLinePlain,
    IconButton,
    QVerticalLabel,
    StopButton,
    ValidButton,
    VLinePlain,
)
from bapsf_motion.utils import SimpleSignal

# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta  # noqa

if TYPE_CHECKING:
    from PySide6.QtGui import QCloseEvent

    from bapsf_motion.gui.configure.configure_ import ConfigureGUI, RMObject


class MGControlAxis(QWidget):
    axisStatusChanged = Signal()

    movementStarted = Signal(int)
    movementStopped = Signal(int)

    def __init__(
        self,
        *,
        rmo: RMObject,
        mg_id: str | int,
        ax_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        self._logger = gui_logger

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

        # Initialize Widgets
        self.axis_name_label = self._init_axis_name_label(self._axis.name)
        self.enable_btn = self._init_enable_btn()
        self.encoder_label = self._init_encoder_label()
        self.encoder_label_icon = self._init_encoder_label_icon()
        self.indicator_column_widget = self._init_indicator_column_widget()
        self.jog_backward_btn = self._init_jog_backward_btn()
        self.jog_delta_input = self._init_jog_delta_input()
        self.jog_delta_icon = self._init_jog_delta_icon()
        self.jog_forward_btn = self._init_jog_forward_btn()
        self.limit_bwd_btn = self._init_limit_bwd_btn()
        self.limit_fwd_btn = self._init_limit_fwd_btn()
        self.mg_details_btn = None
        self.movement_column_widget = self._init_movement_column_widget()
        self.position_label = self._init_position_label()
        self.position_label_icon = self._init_position_label_icon()

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.jog_delta_input.editingFinished.connect(self._validate_jog_delta_input)

    def _define_layout(self):

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
        layout.addLayout(self._define_layout_title_and_enable_btn())
        layout.addSpacing(4)
        layout.addLayout(self._define_layout_position_label())
        layout.addSpacing(4)
        layout.addLayout(self._define_layout_encoder_label())
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

    def _define_layout_title_and_enable_btn(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(8)
        layout.addWidget(self.axis_name_label)
        layout.addStretch(1)
        layout.addWidget(self.enable_btn)
        return layout

    def _define_layout_encoder_label(self):
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

    def _define_layout_position_label(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(
            self.position_label,
            0,
            0,
            5,
            8,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter,
        )
        layout.addWidget(
            self.position_label_icon,
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

    def _init_position_label(self):
        _txt = QLineEdit("", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setReadOnly(True)
        _txt.setToolTip("Motor Position")
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        return _txt

    def _init_position_label_icon(self):
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

    def _actor_slot_movement_started(self):
        self.movementStarted.emit(self._ax_id)

    def _actor_slot_movement_finished(self):
        self.movementStopped.emit(self._ax_id)

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

        for motor_signal, callbacks in self._motor_signal_mapping.items():
            signal = getattr(axis.motor.signals, motor_signal, None)

            if not isinstance(signal, SimpleSignal):
                continue

            for callback in callbacks:
                signal.disconnect(callback)

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

    @Slot()
    def _validate_jog_delta_input(self):
        _txt = self.jog_delta_input.text()
        val = 0.0 if _txt == "" else float(_txt)
        val = abs(val)
        self.jog_delta_input.setText(f"{val:.2f}")

    def closeEvent(self, event: QCloseEvent):
        self.motor_signals_disconnect()
        event.accept()


class MGControl(QWidget):

    def __init__(self, *, rmo: RMObject, motion_group_id: str | int, parent: QWidget):
        super().__init__(parent)
        self._rmo = rmo
        self._mg_id = motion_group_id
        self._mg = self._rmo.rm.mgs[motion_group_id]

        # initialize widgets
        self.drive_name_label = self._init_drive_name_label()
        self.axis_control_widgets = []
        for ax_id in range(len(self._mg.drive.axes)):
            ax_control = MGControlAxis(
                rmo=self._rmo,
                mg_id=self._mg_id,
                ax_id=ax_id,
                parent=self,
            )
            self.axis_control_widgets.append(ax_control)

        self.setLayout(self._define_layout())
        self.setFixedHeight(int(12.5 * 12))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._connect_signals()

    def _connect_signals(self): ...

    def _define_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(self._define_name_layout())
        layout.addLayout(self._define_vdivider_layout())
        layout.addSpacing(8)
        layout.addSpacerItem(
            QSpacerItem(120, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Ignored)
        )
        for ax_widget in self.axis_control_widgets:
            layout.addSpacing(8)
            layout.addLayout(self._define_vdivider_layout())
            layout.addSpacing(8)
            layout.addWidget(ax_widget)

        layout.addSpacing(8)
        layout.addLayout(self._define_vdivider_layout())
        layout.addStretch(1)
        return layout

    def _define_name_layout(self):
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

    def _define_vdivider_layout(self):
        divider = VLinePlain(parent=self)
        divider.set_color(60, 60, 60)
        divider.setLineWidth(2)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addSpacing(8)
        layout.addWidget(divider)
        layout.addSpacing(8)
        return layout

    def _init_drive_name_label(self):
        label = QVerticalLabel(self.mg.drive.name, parent=self)
        label.setObjectName("drive_label")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        font = label.font()
        font.setPixelSize(24)
        font.setBold(True)
        label.setFont(font)
        label.setFixedWidth(32)
        # label.setStyleSheet("""
        # QVerticalLabel#drive_label {
        #     border: 2px solid black;
        #     padding: 0px;
        #     margin: 0px;
        # }
        # """)
        return label

    @property
    def mg(self) -> MotionGroup:
        return self._mg

    def closeEvent(self, event: QCloseEvent):
        self.mg.stop()
        self._mg = None
        event.accept()


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
        self.mgc_widgets = {}

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

    def _spawn_mg_control_widget(self, mg_id):
        _widget = MGControl(
            rmo=self.rmo,
            motion_group_id=mg_id,
            parent=self,
        )
        self.mgc_widgets[mg_id] = _widget

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
    def stop_all(self):
        for mg in self.rm.mgs.values():
            mg.stop()

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
