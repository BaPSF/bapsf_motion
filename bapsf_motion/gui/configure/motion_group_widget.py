__all__ = ["MGWidget"]

import asyncio
import logging

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from typing import Any, Dict, List, Optional, Tuple, Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.actors import Axis, Drive, MotionGroup, MotionGroupConfig
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


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()

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
        if self.mg.drive.is_moving:
            return

        position = self.mg.position.value
        position[self.axis_index] = target_ax_pos

        self.mg.move_to(position)

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
        self._update_display_of_axis_status()

        self.axisLinked.emit()

    def unlink_axis(self):
        if self.axis is not None:
            # self.axis.terminate(delay_loop_stop=True)
            self.axis.motor.status_changed.disconnect(self._update_display_of_axis_status)

        self._mg = None
        self._axis_index = None
        self.axisUnlinked.emit()

    def closeEvent(self, event):
        self.logger.info("Closing AxisControlWidget")
        event.accept()


class DriveControlWidget(QWidget):

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
            acw.show()

        self.setEnabled(not self._mg.terminated)

    def unlink_motion_group(self):
        for ii, acw in enumerate(self._axis_control_widgets):
            visible = True if ii == 0 else False

            acw.unlink_axis()
            acw.setVisible(visible)

        # self.mg.terminate(delay_loop_stop=True)
        self._mg = None
        self.setEnabled(False)

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
        mg_config: Optional[MotionGroupConfig] = None,
        defaults: Optional[Dict[str, Any]] = None,
        parent: Optional["configure_.ConfigureGUI"] = None,
    ):
        super().__init__(parent=parent)

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
        # self._populate_mb_dropdown()

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

        if "transform" not in self.mg_config:
            self._mg_config["transform"] = {"type": "identity"}
        self._initial_mg_config = _deepcopy_dict(self._mg_config)

        self._spawn_motion_group()
        self._refresh_drive_control()

    def _connect_signals(self):
        self.drive_btn.clicked.connect(self._popup_drive_configuration)
        self.transform_btn.clicked.connect(self._popup_transform_configuration)
        self.mb_btn.clicked.connect(self._popup_motion_builder_configuration)

        self.mg_name_widget.editingFinished.connect(self._rename_motion_group)

        self.configChanged.connect(self._update_toml_widget)
        self.configChanged.connect(self._update_mg_name_widget)
        self.configChanged.connect(self._validate_motion_group)
        self.configChanged.connect(self._update_drive_dropdown)

        self.drive_dropdown.currentIndexChanged.connect(self._drive_dropdown_new_selection)

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

    def _build_drive_defaults(self):

        if self._defaults is None or "drive" not in self._defaults:
            self._drive_defaults = [("Custom Drive", {})]
            return self._drive_defaults

        _drive_defaults = {"Custom Drive": {}}
        _defaults = _deepcopy_dict(self._defaults["drive"])  # type: dict
        if "default" in _defaults:
            default_name = _defaults.pop("default")
        else:
            default_name = "Custom Drive"

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

    def _populate_drive_dropdown(self):
        for item in self.drive_defaults:
            self.drive_dropdown.addItem(item[0])

        # set default drive
        self.drive_dropdown.setCurrentIndex(0)

    def _populate_transform_dropdown(self):
        for item in self.transform_defaults:
            self.transform_dropdown.addItem(item[0])

        # set default drive
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
            name = "A New MG" if name == "" else name
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
        self.logger.info("Replacing the motion group's transform.")
        self.mg.replace_transform(config)
        self.configChanged.emit()

    @Slot(object)
    def _change_motion_builder(self, config: Dict[str, Any]):
        self.logger.info("Replacing the motion group's motion builder.")
        self.mg.replace_motion_builder(config)
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

    def _update_toml_widget(self):
        self.toml_widget.setText(toml.as_toml_string(self.mg_config))

    def _update_mg_name_widget(self):
        self.mg_name_widget.setText(self.mg_config["name"])

    def _rename_motion_group(self):
        self.mg.config["name"] = self.mg_name_widget.text()
        self.configChanged.emit()

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
        if not isinstance(self.mg, MotionGroup) or not isinstance(self.mg.drive, Drive):
            self.done_btn.setEnabled(False)
            self.mb_btn.setEnabled(False)
            self.transform_btn.setEnabled(False)
            self.drive_control_widget.setEnabled(False)
            return
        elif not isinstance(self.mg.mb, MotionBuilder):
            self.done_btn.setEnabled(False)
        elif not isinstance(self.mg.transform, BaseTransform):
            self.done_btn.setEnabled(False)
        else:
            self.done_btn.setEnabled(True)

        self.drive_control_widget.setEnabled(True)
        self.mb_btn.setEnabled(True)
        self.transform_btn.setEnabled(True)

    @Slot(int)
    def _drive_dropdown_new_selection(self, index):
        self.logger.warning(f"New selections in drive dropdown {index}")
        if self.drive_dropdown.currentText() == "Custom Drive":
            # custom drive can be anything, change nothing
            return

        drive_config = _deepcopy_dict(self.drive_defaults[index][1])
        self._change_drive(drive_config)

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
