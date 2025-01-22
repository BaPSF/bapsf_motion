__all__ = ["MGWidget"]

import asyncio
import logging
import warnings

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QDoubleValidator
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
from bapsf_motion.gui.configure.transform_overlay import TransformConfigOverlay
from bapsf_motion.gui.widgets import GearValidButton, HLinePlain, StyleButton
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


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()
    movementStarted = Signal(int)
    movementStopped = Signal(int)
    axisStatusChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None
        self._axis_index = None

        self.setFixedWidth(120)
        # self.setEnabled(True)

        # Define BUTTONS
        _btn = StyleButton(qta.icon("fa.arrow-up"), "")
        _btn.setIconSize(QSize(48, 48))
        self.jog_forward_btn = _btn

        _btn = StyleButton(qta.icon("fa.arrow-down"), "")
        _btn.setIconSize(QSize(48, 48))
        self.jog_backward_btn = _btn

        _btn = StyleButton("FWD LIMIT")
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked"
        )
        _btn.setCheckable(True)
        self.limit_fwd_btn = _btn

        _btn = StyleButton("BWD LIMIT")
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 95, 95)"},
            action="checked"
        )
        _btn.setCheckable(True)
        self.limit_bwd_btn = _btn

        _btn = StyleButton("HOME")
        _btn.setEnabled(False)
        self.home_btn = _btn

        _btn = StyleButton("ZERO")
        self.zero_btn = _btn

        # Define TEXT WIDGETS
        _txt = QLabel("Name")
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setFixedHeight(18)
        self.axis_name_label = _txt

        _txt = QLineEdit("")
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _txt.setReadOnly(True)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        self.position_label = _txt

        _txt = QLineEdit("")
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        self.target_position_label = _txt

        _txt = QLineEdit("0")
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        _txt.setValidator(QDoubleValidator(decimals=2))
        self.jog_delta_label = _txt

        # Define ADVANCED WIDGETS

        self.mspace_warning_dialog = None
        if isinstance(parent, DriveControlWidget):
            self.mspace_warning_dialog = parent.mspace_warning_dialog

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.jog_forward_btn.clicked.connect(self._jog_forward)
        self.jog_backward_btn.clicked.connect(self._jog_backward)
        self.zero_btn.clicked.connect(self._zero_axis)
        self.jog_delta_label.editingFinished.connect(self._validate_jog_value)

    def _define_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # layout.addStretch(1)
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
        # layout.addStretch(1)
        layout.addWidget(self.limit_fwd_btn, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.jog_forward_btn)
        layout.addStretch(1)
        layout.addWidget(self.jog_delta_label)
        layout.addWidget(self.home_btn)
        layout.addStretch(1)
        layout.addWidget(self.jog_backward_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(self.limit_bwd_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        # layout.addStretch(1)
        layout.addWidget(self.zero_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        # layout.addStretch(1)
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
            return

        return self.mg.drive.axes[self.axis_index]

    @property
    def position(self) -> u.Quantity:
        position = self.mg.position
        val = position.value[self.axis_index]
        unit = position.unit
        return val * unit

    @property
    def target_position(self):
        return float(self.target_position_label.text())

    def _get_jog_delta(self):
        delta_str = self.jog_delta_label.text()
        return float(delta_str)

    def _jog_forward(self):
        pos = self.position.value + self._get_jog_delta()
        self._move_to(pos)

    def _jog_backward(self):
        pos = self.position.value - self._get_jog_delta()
        self._move_to(pos)

    def _move_to(self, target_ax_pos):
        target_pos = self.mg.position.value
        target_pos[self.axis_index] = target_ax_pos

        if self.mg.drive.is_moving:
            self.logger.info(
                "Probe drive is currently moving.  Did NOT perform move "
                f"to {target_pos}."
            )
            return

        proceed = True
        if not isinstance(self.mg.mb, MotionBuilder):
            proceed = self.mspace_warning_dialog.exec()

        if proceed:
            self.mg.move_to(target_pos)

    def _update_display_of_axis_status(self):
        if self._mg.terminated:
            return

        # pos = self.axis.motor.status["position"]
        pos = self.position
        self.position_label.setText(f"{pos.value:.2f} {pos.unit}")

        if self.target_position_label.text() == "":
            self.target_position_label.setText(f"{pos.value:.2f}")

        limits = self.axis.motor.status["limits"]
        self.limit_fwd_btn.setChecked(limits["CW"])
        self.limit_bwd_btn.setChecked(limits["CCW"])

    def _validate_jog_value(self):
        _txt = self.jog_delta_label.text()
        val = 0.0 if _txt == "" else float(_txt)
        val = abs(val)
        self.jog_delta_label.setText(f"{val:.2f}")

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

    def closeEvent(self, event):
        self.logger.info("Closing AxisControlWidget")

        if isinstance(self.axis, Axis):
            self.axis.motor.status_changed.disconnect(self._update_display_of_axis_status)
            self.axis.motor.status_changed.disconnect(self.axisStatusChanged.emit)
            self.axis.motor.movement_started.connect(self._emit_movement_started)
            self.axis.motor.movement_finished.connect(self._emit_movement_finished)
            self.axis.motor.movement_finished.disconnect(
                self._update_display_of_axis_status
            )

        event.accept()


class DriveControlWidget(QWidget):
    movementStarted = Signal()
    movementStopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = gui_logger

        self._mg = None
        self._axis_control_widgets = []  # type: List[AxisControlWidget]

        self.setEnabled(True)

        # Define BUTTONS

        _btn = StyleButton("STOP")
        _btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        _btn.setFixedWidth(200)
        _btn.setMinimumHeight(400)
        font = _btn.font()
        font.setPointSize(32)
        font.setBold(True)
        _btn.setFont(font)
        _btn.update_style_sheet(
            {
                "background-color": "rgb(255, 75, 75)",
                "border": "3px solid rgb(170, 170, 170)",
            },
        )
        self.stop_1_btn = _btn

        _btn = StyleButton("STOP")
        _btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        _btn.setFixedWidth(200)
        _btn.setMinimumHeight(400)
        font = _btn.font()
        font.setPointSize(32)
        font.setBold(True)
        _btn.setFont(font)
        _btn.update_style_sheet(
            {
                "background-color": "rgb(255, 75, 75)",
                "border": "3px solid rgb(170, 170, 170)",
            },
        )
        self.stop_2_btn = _btn

        _btn = StyleButton("Move \n To")
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(int(.25 * self.stop_1_btn.minimumHeight()))
        font = _btn.font()
        font.setPointSize(26)
        font.setBold(False)
        _btn.setFont(font)
        self.move_to_btn = _btn

        _btn = StyleButton("Home \n All")
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(int(.25 * self.stop_1_btn.minimumHeight()))
        font = _btn.font()
        font.setPointSize(26)
        font.setBold(False)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.home_btn = _btn

        _btn = StyleButton("Zero \n All")
        _btn.setFixedWidth(100)
        _btn.setMinimumHeight(int(.25 * self.stop_1_btn.minimumHeight()))
        font = _btn.font()
        font.setPointSize(26)
        font.setBold(False)
        _btn.setFont(font)
        self.zero_all_btn = _btn

        # Define TEXT WIDGETS
        # Define ADVANCED WIDGETS

        self.mspace_warning_dialog = MSpaceMessageBox(parent=self)

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.stop_1_btn.clicked.connect(self._stop_move)
        self.stop_2_btn.clicked.connect(self._stop_move)
        self.zero_all_btn.clicked.connect(self._zero_drive)
        self.move_to_btn.clicked.connect(self._move_to)

    def _define_layout(self):
        # Sub-Layout #1
        sub_layout = QVBoxLayout()
        sub_layout.addWidget(self.move_to_btn)
        sub_layout.addStretch()
        sub_layout.addWidget(self.home_btn)
        sub_layout.addStretch()
        sub_layout.addWidget(self.zero_all_btn)

        # Sub-Layout #2
        _text = QLabel("Position")
        font = _text.font()
        font.setPointSize(14)
        _text.setFont(font)
        _pos_label = _text

        _text = QLabel("Target")
        font = _text.font()
        font.setPointSize(14)
        _text.setFont(font)
        _target_label = _text

        _text = QLabel("Jog Δ")
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
        sub_layout2.addWidget(
            _target_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addStretch(14)
        sub_layout2.addWidget(
            _jog_delta_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        sub_layout2.addStretch(20)

        # Main Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            self.stop_1_btn,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addLayout(sub_layout)
        layout.addLayout(sub_layout2)
        for ii in range(4):
            acw = AxisControlWidget(self)
            visible = True if ii == 0 else False
            acw.setVisible(visible)
            layout.addWidget(acw)
            self._axis_control_widgets.append(acw)
            layout.addSpacing(2)
        layout.addStretch()
        layout.addWidget(
            self.stop_2_btn,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        return layout

    @property
    def logger(self):
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        return self._mg

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
            return

        proceed = True
        if not isinstance(self.mg.mb, MotionBuilder):
            proceed = self.mspace_warning_dialog.exec()

        if proceed:
            self.mg.move_to(target_pos)

    def _stop_move(self):
        self.mg.stop()

    def _zero_drive(self):
        self.mg.set_zero()

    def link_motion_group(self, mg):
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
            acw.axisStatusChanged.connect(self._update_all_axis_displays)
            acw.show()

        self.setEnabled(not self._mg.terminated)

    def unlink_motion_group(self):
        for ii, acw in enumerate(self._axis_control_widgets):
            visible = True if ii == 0 else False

            acw.unlink_axis()

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                acw.movementStarted.disconnect(self._drive_movement_started)
                acw.movementStopped.disconnect(self._drive_movement_finished)
                acw.axisStatusChanged.disconnect(self._update_all_axis_displays)

            acw.setVisible(visible)

        # self.mg.terminate(delay_loop_stop=True)
        self._mg = None
        self.setEnabled(False)

    def _update_all_axis_displays(self):
        for acw in self._axis_control_widgets:
            if acw.isHidden():
                continue
            elif acw.axis.is_moving:
                continue

            acw._update_display_of_axis_status()

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

    def closeEvent(self, event):
        self.logger.info("Closing DriveControlWidget")
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
                if mg_config is not None and dict_equal(mg_config, mg.config):
                    # assume we are editing an existing motion group
                    continue

                deployed_mg_names.append(mg.config["name"])

                for axis in mg.drive.axes:
                    deployed_ips.append(axis.ip)

        self._deployed_restrictions = {
            "mg_names": deployed_mg_names,
            "ips": deployed_ips,
        }

        self._logger = gui_logger

        self._mg = None
        self._mg_index = None

        self._mg_config = None
        if isinstance(mg_config, MotionGroupConfig):
            self._mg_config = _deepcopy_dict(mg_config)

        self._defaults = None if defaults is None else _deepcopy_dict(defaults)
        self._drive_defaults = None
        self._build_drive_defaults()

        self._transform_defaults = None
        self._build_transform_defaults()

        self._mb_defaults = None
        self._build_mb_defaults()

        # Define TEXT WIDGETS

        _widget = QTextEdit()
        _widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        _widget.setReadOnly(True)
        _widget.font().setPointSize(14)
        _widget.font().setFamily("Courier New")
        _widget.setMinimumWidth(350)
        self.toml_widget = _widget

        _widget = QLineEdit()
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        self.mg_name_widget = _widget

        # Define BUTTONS

        _btn = StyleButton("Add / Update")
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = StyleButton("Discard")
        _btn.setFixedWidth(300)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        font.setBold(True)
        _btn.setFont(font)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 110, 110)"}
        )
        self.discard_btn = _btn

        _btn = StyleButton("Load a Default")
        _btn.setFixedWidth(250)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.quick_mg_btn = _btn
        self.quick_mg_btn.setVisible(False)

        _icon = QLabel(parent=self)
        _icon.setPixmap(qta.icon("mdi.steering").pixmap(24, 24))
        _icon.setMaximumWidth(32)
        _icon.setMaximumHeight(32)
        _icon.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
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

        _icon = QLabel(parent=self)
        _icon.setPixmap(qta.icon("mdi.motion").pixmap(24, 24))
        _icon.setMaximumWidth(32)
        _icon.setMaximumHeight(32)
        _icon.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
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

        _icon = QLabel(parent=self)
        _icon.setPixmap(qta.icon("fa5s.exchange-alt").pixmap(24, 24))
        _icon.setMaximumWidth(32)
        _icon.setMaximumHeight(32)
        _icon.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.transform_label = _icon

        _w = QComboBox(parent=self)
        _w.setEditable(False)
        font = _w.font()
        font.setPointSize(16)
        _w.setFont(font)
        _w.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._transform_dropdown = _w
        self._populate_transform_dropdown()

        _btn = GearValidButton(parent=self)
        _btn.setEnabled(False)
        self.transform_btn = _btn

        # Define ADVANCED WIDGETS
        self._overlay_widget = None  # type: Union[_ConfigOverlay, None]
        self._overlay_shown = False

        self.drive_control_widget = DriveControlWidget(self)
        self.drive_control_widget.setEnabled(False)

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

        self.drive_control_widget.movementStarted.connect(self.disable_config_controls)
        self.drive_control_widget.movementStopped.connect(self.enable_config_controls)

        self.done_btn.clicked.connect(self.return_and_close)
        self.discard_btn.clicked.connect(self.close)

    def _define_layout(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addLayout(self._define_mg_builder_layout(), 2)
        layout.addWidget(HLinePlain(parent=self))
        layout.addWidget(self.drive_control_widget)
        # layout.addStretch(1)

        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()

        layout.addWidget(self.discard_btn)
        layout.addStretch()
        layout.addWidget(self.quick_mg_btn)
        layout.addStretch()
        layout.addWidget(self.done_btn)

        return layout

    def _define_mg_builder_layout(self):
        layout = QHBoxLayout()
        layout.addLayout(self._define_toml_layout())
        layout.addSpacing(12)
        layout.addLayout(self._define_central_builder_layout())
        layout.addSpacing(12)
        layout.addStretch(1)

        return layout

    def _def_mg_control_layout(self):
        ...

    def _define_toml_layout(self):
        label = QLabel("Motion Group Configuration")
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

    def _define_central_builder_layout(self):

        _label = QLabel("Name:  ")
        _label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt. AlignmentFlag.AlignLeft
        )
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        name_label = _label

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(name_label)
        sub_layout.addWidget(self.mg_name_widget)

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

        layout = QVBoxLayout()
        layout.addSpacing(18)
        layout.addLayout(sub_layout)
        layout.addSpacing(18)
        layout.addLayout(drive_sub_layout)
        layout.addLayout(mb_sub_layout)
        layout.addLayout(transform_sub_layout)
        layout.addStretch()

        return layout

    def _define_mspace_display_layout(self):
        ...

    def _build_drive_defaults(self) -> List[Tuple[str, Dict[str, Any]]]:
        # Returned _drive_defaults is a List of Tuple pairs
        # - 1st Tuple element is the dropdown name
        # - 2nd Tuple element is the dictionary configuration
        if self._defaults is None or "drive" not in self._defaults:
            self._drive_defaults = [("Custom Drive", {})]
            return self._drive_defaults

        _drive_defaults = {"Custom Drive": {}}
        _defaults = _deepcopy_dict(self._defaults["drive"])  # type: dict
        default_name = _defaults.pop("default", "Custom Drive")

        # populate defaults dict
        if "name" in _defaults.keys():
            # only one drive defined
            _name = _defaults["name"]
            if _name not in _drive_defaults.keys():
                _drive_defaults[_name] = _deepcopy_dict(_defaults)
        else:
            for key, entry in _defaults.items():
                _name = entry["name"]
                if _name in _drive_defaults.keys():
                    # do not add duplicate defaults
                    continue

                _drive_defaults[_name] = _deepcopy_dict(entry)

        # convert to list of 2-element tuples
        self._drive_defaults = []
        for key, val in _drive_defaults.items():
            if key == default_name:
                self._drive_defaults.insert(0, (key, val))
            else:
                self._drive_defaults.append((key, val))

        return self._drive_defaults

    def _build_mb_defaults(self):
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
        self._transform_defaults = [("Custom Transform", {})]
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

        # updating the drive control widget should always be the last
        # step
        self._update_drive_control_widget()

    def _populate_drive_dropdown(self):
        for item in self.drive_defaults:
            self.drive_dropdown.addItem(item[0])

        # set default drive
        self.drive_dropdown.setCurrentIndex(0)

    def _populate_mb_dropdown(self):
        self.logger.info("Populating Motion Builder dropdown")

        mb_name_stored = (
            None if self.mb_dropdown.count() == 0
            else self.mb_dropdown.currentText()
        )

        # Block signals when repopulating the dropdown
        self.mb_dropdown.blockSignals(True)

        self.mb_dropdown.clear()

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

                self.mb_dropdown.setCurrentIndex(index)
                return

        index = self.mb_dropdown.findText("Custom Motion Builder")
        self.mb_dropdown.setCurrentIndex(index)

    def _populate_transform_dropdown(self):

        if self.transform_dropdown.count() != 0:
            # we are repopulating and need to reset dropdown to current position
            tr_name_stored = self.transform_dropdown.currentText()
        else:
            tr_name_stored = None

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
        for tr_name, tr_config in self.transform_defaults:
            index = self.transform_dropdown.findText(tr_name)
            if index != -1:
                # transform already in dropdown
                continue

            if tr_name == "Custom Transform":
                pass
            elif (
                "type" not in tr_config
                or tr_config["type"] not in allowed_transforms
            ):
                continue

            self.transform_dropdown.addItem(tr_name)

        if tr_name_stored is not None:
            index = self.transform_dropdown.findText(tr_name_stored)

            if index != -1:
                self.transform_dropdown.setCurrentIndex(index)
                self.transform_dropdown.blockSignals(False)
                return

        self.transform_dropdown.blockSignals(False)

        # set default transform
        if (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mg.transform, BaseTransform)
        ):
            self.transform_dropdown.setCurrentIndex(0)
            return

        _type = self.mg.transform.transform_type
        _config = _deepcopy_dict(self.mg.transform.config)
        for tr_name, tr_default_config in self.transform_defaults:
            if tr_name == "Custom Transform" or _type != tr_default_config["type"]:
                continue

            if dict_equal(_deepcopy_dict(_config), tr_default_config):
                index = self.transform_dropdown.findText(tr_name)
                if index == -1:
                    # this should not happen
                    break

                self.transform_dropdown.setCurrentIndex(index)
                return

        index = self.transform_dropdown.findText("Custom Transform")
        self.transform_dropdown.setCurrentIndex(index)

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
            self.mg.terminate(delay_loop_stop=True)
            self.drive_control_widget.setEnabled(False)
            self.transform_btn.set_invalid()

        self.mg.replace_transform(_deepcopy_dict(config))

        self.configChanged.emit()

    @Slot(object)
    def _change_motion_builder(self, config: Dict[str, Any]):
        self.logger.info("Replacing the motion group's motion builder.")
        self.mg.replace_motion_builder(_deepcopy_dict(config))
        self.configChanged.emit()

    def _rerun_drive(self):
        self.logger.info("Restarting the motion group's drive")

        if self.mg.drive is None:
            return

        drive_config = self.mg.drive.config
        self._change_drive(drive_config)

    def _refresh_drive_control(self):
        self.logger.info("Refreshing drive control widget.")
        if self.mg is None or self.mg.drive is None:
            self.drive_control_widget.unlink_motion_group()
            return

        self.drive_control_widget.link_motion_group(self.mg)

    def _update_drive_dropdown(self):
        custom_drive_index = self.drive_dropdown.findText("Custom Drive")
        if custom_drive_index == -1:
            raise ValueError("Custom Drive not found")

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

        drive_config_default = self.drive_defaults[index][1]
        if dict_equal(drive_config, drive_config_default):
            self.drive_dropdown.setCurrentIndex(index)
        else:
            self.drive_dropdown.setCurrentIndex(custom_drive_index)

    def _update_mb_dropdown(self):
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

        if self.drive_control_widget.mg is None:
            self._refresh_drive_control()
        else:
            self.drive_control_widget._update_all_axis_displays()

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
            self.mg.terminate(delay_loop_stop=True)
            # self._set_mg(None)
            self._mg = None

        try:
            mg = MotionGroup(
                config=self.mg_config,
                logger=logging.getLogger(f"{self.logger.name}.MGW"),
                loop=self.mg_loop,
                auto_run=True,
            )
        except (ConnectionError, TimeoutError, ValueError, TypeError):
            self.logger.warning("Not able to instantiate MotionGroup.")
            mg = None

        self._set_mg(mg)

        return mg

    def _validate_motion_group(self):
        self.logger.info("Validating motion group")

        vmg_name = self._validate_motion_group_name()
        vdrive = self._validate_drive()

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
        else:
            if "layer" not in mb.config:
                self.mb_btn.set_invalid()
                self.mb_btn.setToolTip(
                    "A point layer needs to be defined to generate a motion list."
                )
            else:
                self.mb_btn.set_valid()
                self.mb_btn.setToolTip("")

        if not isinstance(transform, BaseTransform):
            self.transform_btn.set_invalid()
            self.done_btn.setEnabled(False)

            self.drive_control_widget.setEnabled(False)
        else:
            self.transform_btn.set_valid()
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

            self.mb_dropdown.setEnabled(False)
            self.mb_btn.setEnabled(False)
            self.mb_btn.set_invalid()
            self.mb_btn.setToolTip("Motion space needs to be defined.")

            self.transform_dropdown.setEnabled(False)
            self.transform_btn.setEnabled(False)
            self.transform_btn.set_invalid()

            self.drive_btn.set_invalid()
            self.drive_control_widget.setEnabled(False)

            self.drive_btn.setToolTip("Drive is not fully configured.")
            return False

        self.mb_dropdown.setEnabled(True)
        self.mb_btn.setEnabled(True)

        self.transform_dropdown.setEnabled(True)
        self.transform_btn.setEnabled(True)

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
        self.logger.warning(f"New selections in drive dropdown {index}")
        if self.drive_dropdown.currentText() == "Custom Drive":
            # custom drive can be anything, change nothing
            return

        drive_config = _deepcopy_dict(self.drive_defaults[index][1])
        self._change_drive(drive_config)

    @Slot(int)
    def _mb_dropdown_new_selection(self, index):
        mb_name = self.mb_dropdown.currentText()
        self.logger.warning(
            f"New selections in motion builder dropdown {index} '{mb_name}'"
        )

        if index == -1:
            return
        elif mb_name == "Custom Motion Builder":
            # custom transform can be anything, change nothing
            return

        mb_default_config = None  # type: Union[Dict[str, Any], None]
        for _name, _config in self.mb_defaults:
            if mb_name != _name:
                continue

            mb_default_config = _deepcopy_dict(_config)
            break

        self.logger.info(f"New MB config...\n{mb_default_config}")
        self.logger.info(
            f"mb_default_config is None = {mb_default_config is None}\n"
            f"'motion_builder' in self.mg_config = {'motion_builder' in self.mg_config}\n"
        )
        if mb_default_config is None:
            # could not find the default config
            self._update_mb_dropdown()
            return
        elif (
            "motion_builder" in self.mg_config
            and dict_equal(
                mb_default_config,
                _deepcopy_dict(self.mg_config["motion_builder"]),
            )
        ):
            self.logger.info(
                "Selected transform is already in use\n"
                f"selected = {mb_default_config}\n"
                f"old = {_deepcopy_dict(self.mg_config['motion_builder'])}"
            )
            # selected transform is already deployed
            return

        self.logger.info("Changing MB config...")
        self._change_motion_builder(mb_default_config)

    @Slot(int)
    def _transform_dropdown_new_selection(self, index):
        tr_name = self.transform_dropdown.currentText()
        self.logger.warning(f"New selections in transform dropdown {index} '{tr_name}'")

        if index == -1:
            return
        elif tr_name == "Custom Transform":
            # custom transform can be anything, change nothing
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
        self.drive_dropdown.setEnabled(True)
        self.drive_btn.setEnabled(True)

        self.mb_dropdown.setEnabled(True)
        self.mb_btn.setEnabled(True)

        self.transform_dropdown.setEnabled(True)
        self.transform_btn.setEnabled(True)

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

        loop_safe_stop(self.mg_loop)
        self.closing.emit()
        event.accept()
