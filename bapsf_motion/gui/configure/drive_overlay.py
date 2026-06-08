"""
Module contains the functionality associated with the |Drive|
configuration overlay portion of the configuration GUI.
"""

__all__ = ["AxisConfigWidget", "DriveConfigOverlay"]

import ast
import asyncio
import logging
import warnings

from functools import partial
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from typing import Any, Callable, Dict, List, Union

from bapsf_motion.actors import Axis, Drive, MotionGroup, Motor
from bapsf_motion.gui.configure import motion_group_widget as mgw
from bapsf_motion.gui.configure.bases import _ConfigOverlay
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.widgets import (
    HLinePlain,
    IPv4Validator,
    LED,
    QDoublePinnedValidator,
    StyleButton,
    VLinePlain,
)
from bapsf_motion.utils import _deepcopy_dict, dict_equal, ipv4_pattern, loop_safe_stop


class AxisConfigWidget(QWidget):
    configChanged = Signal()

    def __init__(self, name, parent=None):
        super().__init__(parent=parent)

        self.axis_loop = asyncio.new_event_loop()
        self._logger = logging.getLogger(f"{gui_logger.name}.ACW")
        self._ip_handlers = []

        self._axis_config = {
            "name": name,
            "units": "cm",
            "ip": "",
            "units_per_rev": "",
            "motor_settings": {
                "current": 0.8,
                "limit_mode": 1,
                "speed": 4.0,
            },
        }
        self._axis = None

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        # Define BUTTONS
        _btn = LED(parent=self)
        _btn.set_fixed_height(24)
        self.online_led = _btn

        # Define TEXT WIDGETS
        _widget = QLabel(name, parent=self)
        font = _widget.font()
        font.setPointSize(32)
        _widget.setFont(font)
        _widget.setFixedWidth(30)
        self.ax_name_widget = _widget

        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        _widget.setInputMask("009.009.009.009;_")
        _widget.setValidator(IPv4Validator(logger=self._logger))
        self.ip_widget = _widget

        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setFixedWidth(120)
        _widget.setValidator(QDoubleValidator(decimals=4))
        _widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cm_per_rev_widget = _widget

        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setFixedWidth(100)
        _widget.setValidator(QDoublePinnedValidator(bottom=0.5, top=15.0, decimals=1))
        _widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_input = _widget

        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setFixedWidth(100)
        _widget.setValidator(QDoublePinnedValidator(bottom=0.5, top=1.0, decimals=2))
        _widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_input = _widget

        # Define ADVANCED WIDGETS
        _widget = QSlider(Qt.Orientation.Horizontal, parent=self)
        _widget.setMinimum(1)
        _widget.setMaximum(3)
        _widget.setTickInterval(1)
        _widget.setSingleStep(1)
        _widget.setTickPosition(QSlider.TickPosition.TicksBothSides)
        _widget.setFixedHeight(24)
        _widget.setMinimumWidth(100)
        _widget.setValue(1)
        self.limit_mode_slider = _widget

        speed_validator = self.speed_input.validator()  # type: QDoubleValidator
        min_tick = int(speed_validator.bottom() / 0.1)
        max_tick = int(speed_validator.top() / 0.1)
        _widget = QSlider(Qt.Orientation.Horizontal, parent=self)
        _widget.setMinimum(min_tick)
        _widget.setMaximum(max_tick)
        _widget.setTickInterval(10)
        _widget.setSingleStep(1)
        _widget.setTickPosition(QSlider.TickPosition.TicksBothSides)
        _widget.setFixedHeight(24)
        _widget.setMinimumWidth(100)
        _widget.setValue(0)
        self.speed_slider = _widget

        current_validator = self.current_input.validator()  # type: QDoubleValidator
        min_tick = int(current_validator.bottom() / 0.05)
        max_tick = int(current_validator.top() / 0.05)
        _widget = QSlider(Qt.Orientation.Horizontal, parent=self)
        _widget.setMinimum(min_tick)
        _widget.setMaximum(max_tick)
        _widget.setTickInterval(2)
        _widget.setSingleStep(1)
        _widget.setTickPosition(QSlider.TickPosition.TicksBothSides)
        _widget.setFixedHeight(24)
        _widget.setMinimumWidth(100)
        _widget.setValue(0)
        self.current_slider = _widget

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.ip_widget.editingFinished.connect(self._change_ip_address)
        self.cm_per_rev_widget.editingFinished.connect(self._change_cm_per_rev)
        self.limit_mode_slider.valueChanged.connect(self._change_limit_mode)
        self.speed_input.editingFinished.connect(self._change_speed_from_field)
        self.speed_slider.valueChanged.connect(self._change_speed_from_slider)

        self.configChanged.connect(self._update_ip_widget)
        self.configChanged.connect(self._update_cm_per_rev_widget)
        self.configChanged.connect(self._update_online_led)
        self.configChanged.connect(self._update_limit_mode_widget)
        self.configChanged.connect(self._update_speed_widgets)

    def _define_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            self.ax_name_widget,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addSpacing(12)
        layout.addLayout(self._define_ip_input_layout())
        layout.addLayout(self._define_vdivider_layout())
        layout.addLayout(self._define_cm_per_rev_layout())
        layout.addLayout(self._define_vdivider_layout())
        layout.addLayout(self._define_limit_mode_layout())
        layout.addLayout(self._define_vdivider_layout())
        layout.addWidget(self._define_speed_input_widget())
        layout.addLayout(self._define_vdivider_layout())
        layout.addStretch()
        layout.addLayout(self._define_vdivider_layout())
        layout.addLayout(self._define_online_indicator_layout())
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

    def _define_ip_input_layout(self):
        _label = QLabel("IP:", parent=self)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        ip_label = _label

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            ip_label,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addSpacing(4)
        layout.addWidget(
            self.ip_widget,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        return layout

    def _define_cm_per_rev_layout(self):
        _label = QLabel("cm / rev", parent=self)
        font = _label.font()
        font.setPointSize(12)
        _label.setFont(font)
        _label.setContentsMargins(0, 0, 0, 0)
        cm_per_rev_label = _label

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(
            self.cm_per_rev_widget,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addSpacing(-8)
        layout.addWidget(
            cm_per_rev_label,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch(1)
        return layout

    def _define_limit_mode_layout(self):
        _label = QLabel("Limit\nMode", parent=self)
        _label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)

        _energized_label = QLabel("energized", parent=self)
        _energized_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        font = _energized_label.font()
        font.setPointSize(12)
        _energized_label.setFont(font)

        _deenergized_label = QLabel("de-energized", parent=self)
        _deenergized_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        font = _deenergized_label.font()
        font.setPointSize(12)
        _deenergized_label.setFont(font)

        _none_label = QLabel("NONE", parent=self)
        _none_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        font = _none_label.font()
        font.setPointSize(12)
        _none_label.setFont(font)

        slider_layout = QGridLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.addWidget(self.limit_mode_slider, 1, 2, 1, 7)
        slider_layout.addWidget(_energized_label, 0, 1, 1, 3)
        slider_layout.addWidget(_deenergized_label, 2, 4, 1, 3)
        slider_layout.addWidget(_none_label, 0, 7, 1, 3)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _label,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addSpacing(8)
        layout.addLayout(slider_layout)
        return layout

    def _define_speed_input_widget(self):
        speed_validator = self.speed_input.validator()  # type: QDoubleValidator
        min_speed = speed_validator.bottom()
        max_speed = speed_validator.top()

        min_speed_label = QLabel(f"{min_speed:.1f}", parent=self)
        font = min_speed_label.font()
        font.setPointSize(12)
        min_speed_label.setFont(font)
        min_speed_label.setStyleSheet("margin: 0px;")

        max_speed_label = QLabel(f"{max_speed:.1f}", parent=self)
        font = max_speed_label.font()
        font.setPointSize(12)
        max_speed_label.setFont(font)
        max_speed_label.setStyleSheet("margin: 0px;")

        speed_label = QLabel(f"SPEED", parent=self)
        font = speed_label.font()
        font.setPointSize(10)
        speed_label.setFont(font)
        speed_label.setStyleSheet("margin: 0px;")

        unit_label = QLabel(f"rev / s", parent=self)
        font = unit_label.font()
        font.setPointSize(12)
        unit_label.setFont(font)
        unit_label.setStyleSheet("margin: 0px;")

        slider_number_layout = QHBoxLayout()
        slider_number_layout.setContentsMargins(0, 0, 0, 0)
        slider_number_layout.addWidget(
            min_speed_label, alignment=Qt.AlignmentFlag.AlignLeft
        )
        slider_number_layout.addStretch(1)
        slider_number_layout.addWidget(
            max_speed_label, alignment=Qt.AlignmentFlag.AlignRight
        )

        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.addSpacing(4)
        slider_layout.addWidget(self.speed_slider)
        slider_layout.addSpacing(4)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.speed_input)
        input_layout.addSpacing(4)
        input_layout.addWidget(
            unit_label,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            speed_label,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        layout.addSpacing(-20)
        layout.addLayout(slider_number_layout)
        layout.addLayout(slider_layout)
        layout.addLayout(input_layout)

        widget = QWidget(parent=self)
        widget.setLayout(layout)
        widget.setStyleSheet("margin: 0px;")
        widget.setMinimumWidth(150)
        return widget

    def _define_online_indicator_layout(self):

        _label = QLabel("Online?", parent=self)
        font = _label.font()
        font.setPointSize(12)
        _label.setFont(font)
        online_label = _label

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        layout.addWidget(
            online_label,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(
            self.online_led,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch(1)

        return layout

    @property
    def logger(self):
        return self._logger

    @property
    def axis(self) -> Union[Axis, None]:
        return self._axis

    @axis.setter
    def axis(self, ax: Union[Axis, None]):
        if not (isinstance(ax, Axis) or ax is None):
            return

        self._axis = ax
        self.configChanged.emit()

    @property
    def axis_config(self):
        if isinstance(self.axis, Axis):
            self._axis_config = self.axis.config.copy()
        return self._axis_config

    @axis_config.setter
    def axis_config(self, config):
        _axis_config = {**self.axis_config, **config}

        if (
            isinstance(self.axis, Axis)
            and dict_equal(_axis_config, self.axis.config)
            and not self.axis.terminated
        ):
            # nothing has changed
            return

        if isinstance(self.axis, Axis):
            # configuration has changed and is different from current axis actor
            self.blockSignals(True)
            self.axis.terminate(delay_loop_stop=True)
            self.axis = None
            self.blockSignals(False)

        self._axis_config = _axis_config

        self.blockSignals(True)
        self._check_axis_completeness()
        self.blockSignals(False)
        self.configChanged.emit()

    def _check_axis_completeness(self):
        if isinstance(self.axis, Axis):
            return self.axis.connected

        _completeness = {"name", "ip", "units", "units_per_rev"}
        if _completeness - set(self.axis_config.keys()):
            return False
        elif any([self.axis_config[key] == "" for key in _completeness]):
            return False

        self._spawn_axis()
        if isinstance(self.axis, Axis):
            return self.axis.connected

        return False

    @Slot()
    def _change_cm_per_rev(self):
        try:
            new_cpr = float(self.cm_per_rev_widget.text())
        except ValueError as err:
            self.logger.error(f"{err.__class__.__name__}: {err}")
            self.logger.error(f"Given cm / rev conversion must be a number.")
            self.configChanged.emit()
            return

        config = self.axis_config
        config["units_per_rev"] = new_cpr
        self.axis_config = config

    @Slot()
    def _change_ip_address(self):
        new_ip = self.ip_widget.text()
        new_ip = self._validate_ip(new_ip)
        if new_ip is None:
            # ip was not valid
            self.configChanged.emit()
            return

        old_ip = self.axis_config["ip"]
        if old_ip == new_ip:
            # nothing has changed
            return

        config = self.axis_config
        config["ip"] = new_ip
        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)
            self.axis = None

        self.axis_config = config

    @Slot()
    def _change_limit_mode(self):
        axis_config = self.axis_config.copy()
        old_limit_mode = axis_config["motor_settings"].get("limit_mode", None)

        limit_mode = self.limit_mode_slider.value()

        if old_limit_mode is not None and old_limit_mode == limit_mode:
            # limit_mode did not change
            return

        self._set_limit_mode(limit_mode)

    @Slot()
    def _change_speed_from_slider(self):
        axis_config = self.axis_config.copy()
        old_speed = axis_config["motor_settings"].get("speed", None)

        speed = 0.1 * self.speed_slider.value()
        speed = self._validate_speed(speed)

        if old_speed is not None and old_speed == speed:
            # speed did not change
            return

        self._set_motor_speed(speed)

    @Slot()
    def _change_speed_from_field(self):
        axis_config = self.axis_config.copy()
        old_speed = axis_config["motor_settings"].get("speed", None)

        speed = ast.literal_eval(self.speed_input.text())
        speed = self._validate_speed(speed)

        if old_speed is not None and old_speed == speed:
            # speed did not change
            return

        self._set_motor_speed(speed)

    def _validate_speed(self, speed: float) -> float:
        speed_validator = self.speed_input.validator()  # type: QDoubleValidator
        min_speed = speed_validator.bottom()
        max_speed = speed_validator.top()

        speed = round(speed, 1)
        if speed < min_speed:
            speed = min_speed
        elif speed > max_speed:
            speed = max_speed

        return speed

    def _spawn_axis(self) -> Union[Axis, None]:
        self.logger.info("Spawning Axis.")
        if isinstance(self.axis, Axis):
            self.blockSignals(True)
            self.axis.terminate(delay_loop_stop=True)
            self.axis = None
            self.blockSignals(False)

        try:
            axis = Axis(
                **self.axis_config,
                logger=logging.getLogger(f"{self.logger.name}.AC"),
                loop=self.axis_loop,
                auto_run=True,
            )

            axis.motor.signals.connection_established.connect(self.configChanged.emit)
            axis.motor.signals.connection_lost.connect(self.configChanged.emit)
        except ConnectionError:
            axis = None

        self.axis = axis
        return axis

    @Slot()
    def _update_cm_per_rev_widget(self):
        self.cm_per_rev_widget.setText(f"{self.axis_config['units_per_rev']}")

    @Slot()
    def _update_ip_widget(self):
        self.logger.info(f"Updating IP widget with {self.axis_config['ip']}")
        self.ip_widget.setText(self.axis_config["ip"])

    @Slot()
    def _update_online_led(self):
        online = False
        if isinstance(self.axis, Axis):
            online = self.axis.connected

        self.online_led.setChecked(online)

    @Slot()
    def _update_limit_mode_widget(self):
        limit_mode = self.axis_config["motor_settings"]["limit_mode"]
        self.limit_mode_slider.setValue(limit_mode)

    @Slot()
    def _update_speed_widgets(self):
        speed = self.axis_config["motor_settings"].get("speed", 4.0)
        slider_value = int(speed / 0.1)

        self.logger.info(f"--> Updating speed widgets {speed} {slider_value}")

        self.speed_input.blockSignals(True)
        self.speed_slider.blockSignals(True)

        self.speed_input.setText(f"{speed:.1f}")
        self.speed_slider.setValue(slider_value)

        self.speed_input.blockSignals(False)
        self.speed_slider.blockSignals(False)

    def _validate_ip(self, ip):
        if ip == self.axis_config["ip"]:
            # ip did not change
            return ip
        elif ipv4_pattern.fullmatch(ip) is None:
            self.logger.error(f"Supplied IP address ({ip}) is not a valid IPv4.")
            return

        for handler in self._ip_handlers:
            ip = handler(ip)

            if ip is None or ip == "":
                return

        return ip

    def set_ip_handler(self, handler: callable):
        self._ip_handlers.append(handler)

    def _set_motor_speed(self, speed: float | int):

        if isinstance(self.axis, Axis) and isinstance(self.axis.motor, Motor):
            self.axis.motor.send_command("set_speeds", speed)

            motor_speed = float(self.axis.motor.config["speed"])
            if motor_speed == speed:
                self.configChanged.emit()
                return

        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)
            self.axis = None

        axis_config = self.axis_config.copy()
        axis_config["motor_settings"]["speed"] = speed
        self.axis_config = axis_config

    def _set_limit_mode(self, limit_mode: int):

        if isinstance(self.axis, Axis) and isinstance(self.axis.motor, Motor):
            self.axis.motor.send_command("set_limit_mode", limit_mode)

            motor_limit_mode = self.axis.motor.config["limit_mode"]
            if motor_limit_mode == limit_mode:
                self.configChanged.emit()
                return

        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)
            self.axis = None

        axis_config = self.axis_config.copy()
        axis_config["motor_settings"]["limit_mode"] = limit_mode
        self.axis_config = axis_config

    def closeEvent(self, event):
        self.logger.info("Closing AxisConfigWidget")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                self.configChanged.disconnect()
        except RuntimeError:
            # everything already disconnected
            pass

        if isinstance(self.axis, Axis) and not self.axis.terminated:
            self.axis.terminate(delay_loop_stop=True)

        loop_safe_stop(self.axis_loop)

        event.accept()


class DriveConfigOverlay(_ConfigOverlay):
    drive_loop = asyncio.new_event_loop()

    def __init__(self, mg: MotionGroup, parent: "mgw.MGWidget" = None):
        super().__init__(mg, parent)
        self._logger = logging.getLogger(f"{self.logger.name}.DCO")

        self._drive_handlers = []

        self._drive = None
        self._drive_config = None
        self._axis_widgets = None

        # Define BUTTONS

        _btn = StyleButton("Add Axis", parent=self)
        _btn.setFixedWidth(120)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        _btn.setEnabled(False)
        _btn.setHidden(True)
        self.add_axis_btn = _btn

        _btn = StyleButton("Validate", parent=self)
        _btn.setFixedWidth(150)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        self.validate_btn = _btn

        _btn = LED(parent=self)
        _btn.set_fixed_height(32)
        _btn.off_color = "d43729"
        self.validate_led = _btn

        # Define TEXT WIDGETS
        _widget = QLineEdit(parent=self)
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        self.dr_name_widget = _widget

        # Define ADVANCED WIDGETS

        # initialize drive configuration
        _drive_config = None
        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            self.mg.drive.terminate(delay_loop_stop=True)
            _drive_config = _deepcopy_dict(self.mg.drive.config)
        elif not isinstance(parent, mgw.MGWidget):
            pass
        elif parent.drive_dropdown.currentText != "Custom Drive":
            index = parent.drive_dropdown.currentIndex()
            _drive_config = _deepcopy_dict(parent.drive_defaults[index][1])
        elif "drive" in parent._initial_mg_config:
            _drive_config = _deepcopy_dict(parent._initial_mg_config["drive"])

        self._drive_config = _drive_config

        # initialize widgets
        self.setLayout(self._define_layout())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()

        self.validate_btn.clicked.connect(self._validate_drive)

        self.configChanged.connect(self._update_dr_name_widget)

        self.dr_name_widget.editingFinished.connect(self._change_drive_name)

    def _define_layout(self):

        layout = QVBoxLayout()
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addLayout(self._define_second_row_layout())
        layout.addSpacing(24)

        drive_config = self._drive_config
        for ii, name in enumerate(("X", "Y")):
            layout.addWidget(self._spawn_axis_widget(name))

            # initialize axis widget
            if "axes" in drive_config:
                try:
                    ax_config = drive_config["axes"][ii]
                    self.axis_widgets[ii].axis_config = ax_config
                except KeyError:
                    continue

        layout.addStretch(1)

        return layout

    def _define_banner_layout(self):

        layout = QHBoxLayout()
        layout.addWidget(self.discard_btn)
        layout.addStretch()
        layout.addWidget(self.done_btn)
        return layout

    def _define_second_row_layout(self):
        _label = QLabel("Drive Name:  ", parent=self)
        _label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        name_label = _label

        self._update_dr_name_widget()

        layout = QHBoxLayout()
        layout.addSpacing(18)
        layout.addWidget(name_label)
        layout.addWidget(self.dr_name_widget)
        layout.addStretch()
        layout.addWidget(self.add_axis_btn)
        layout.addStretch()
        layout.addWidget(self.validate_btn)
        layout.addWidget(self.validate_led)
        layout.addSpacing(18)

        return layout

    @property
    def drive(self) -> Union[Drive, None]:
        return self._drive

    def _set_drive(self, dr: Union[Drive, None]):
        if not (isinstance(dr, Drive) or dr is None):
            return

        self._drive = dr
        self.configChanged.emit()

    @property
    def drive_config(self) -> Dict[str, Any]:
        if isinstance(self.drive, Drive):
            self._drive_config = self.drive.config.copy()
            return self._drive_config
        elif self._drive_config is None:
            name = self.dr_name_widget.text()
            name = "A New Drive" if name == "" else name
            self._drive_config = {"name": name}

        if "axes" not in self._drive_config:
            self._drive_config["axes"] = {}

        for ii, axw in enumerate(self.axis_widgets):
            self._drive_config["axes"][ii] = axw.axis_config

        return self._drive_config

    @property
    def axis_widgets(self) -> List[AxisConfigWidget]:
        if self._axis_widgets is None:
            self._axis_widgets = []

        return self._axis_widgets

    @property
    def axis_ips(self):
        if len(self.axis_widgets) == 0:
            return []

        return [axw.axis_config["ip"] for axw in self.axis_widgets]

    @Slot()
    def _change_drive_name(self):
        self.logger.info("Renaming drive...")
        new_name = self.dr_name_widget.text()
        if isinstance(self.drive, Drive):
            self.drive.name = new_name
        else:
            self.drive_config["name"] = new_name

        self.configChanged.emit()

    @Slot()
    def _change_validation_state(self, validate=False):
        self.logger.info(f"Changing validation state to {validate}.")
        self.validate_led.setChecked(validate)
        self.done_btn.setEnabled(validate)

        if not validate:
            self._set_drive(None)

    @Slot()
    def _update_dr_name_widget(self):
        name = self.drive_config.get("name", "")
        self.dr_name_widget.setText(name)

    def set_drive_handler(self, handler: Callable): ...

    def _validate_ip(self, ip):
        existing_ips = self.axis_ips
        if ip in existing_ips:
            self.logger.error(
                f"Supplied IP ({ip}) already exists amongst instantiated axes."
            )
            return

        return ip

    @Slot()
    def _validate_drive(self):
        # What to validate?
        # 1. All axis widgets have an instantiated axis.
        # 2. All instantiated axes are online.
        # 3. The drive has a name
        # 4. The current axis IPs do not overlap with IP in other
        #    motion groups in the run
        # 5. The drive is instantiable Drive()
        self.logger.info("Validating drive.")

        if not all([isinstance(axw.axis, Axis) for axw in self.axis_widgets]):
            self.logger.warning("Drive is not valid since not all axes are configured.")
            self._change_validation_state(False)
            return
        elif not all([axw.axis.connected for axw in self.axis_widgets]):
            self.logger.warning("Drive is not valid since not all axes are online.")
            self._change_validation_state(False)
            return
        elif self.dr_name_widget.text() == "":
            self.logger.warning("Drive is not valid, it needs a name.")
            self._change_validation_state(False)
            return

        # TODO: NEED AN HANDLER THAT ENSURES NO OTHER MOTION GROUP USES
        #       A DRIVE WITH THE SAME IPs
        # for handler in self._drive_handlers:
        #     rtn = handler(self.drive_config)
        #     if not rtn:
        #         self.logger.info("Drive configuration is NOT valid.")
        #         return

        self._spawn_drive()

        self.logger.info("Drive configuration is valid.")

        self._change_validation_state(True)

    def _spawn_axis_widget(self, name):
        _frame = QFrame(parent=self)
        _frame.setLayout(QVBoxLayout())

        _widget = AxisConfigWidget(name, parent=self)
        _widget.set_ip_handler(self._validate_ip)
        _widget.configChanged.connect(
            partial(self._change_validation_state, validate=False),
        )

        self.axis_widgets.append(_widget)

        _frame.layout().addWidget(_widget)
        _frame.setObjectName("acw_frame")
        _frame.setStyleSheet("""
            QFrame#acw_frame {
                border: 2px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 6px;
                margine: 0px;
            }
            """)

        return _frame

    def _spawn_drive(self, config=None):
        self.logger.info(f"Spawning Drive. {self.drive_config}")
        if isinstance(self.drive, Drive):
            self.drive.terminate(delay_loop_stop=True)
            self._set_drive(None)

        for axw in self.axis_widgets:
            if axw.axis is None:
                continue
            axw.axis.terminate(delay_loop_stop=True)

        config = config if config is not None else self.drive_config
        try:
            drive = Drive(
                name=config["name"],
                axes=list(config["axes"].values()),
                logger=logging.getLogger(f"{self.logger.name}.DC"),
                loop=self.drive_loop,
                auto_run=False,
            )

            # we do NOT want the drive actor to be running, since the
            # AxisConfigWidgets will have running Axis actors
            #
            drive.terminate(delay_loop_stop=True)

            # update Axis actors
            for ii, ax in enumerate(drive.axes):
                self.axis_widgets[ii].axis_config = ax.config

        except (ConnectionError, TimeoutError, KeyError):
            self.logger.warning("Not able to instantiate Drive.")
            drive = None

        # restart Axis actors
        for axw in self.axis_widgets:
            if isinstance(axw.axis, Axis) and axw.axis.terminated:
                axw.axis.run()

        self._set_drive(drive)

        return drive

    def _safe_return_config_emit(self, config: Dict[str, Any]):
        self.configChanged.disconnect()
        if isinstance(self.drive, Drive) and not self.drive.terminated:
            self.drive.terminate(delay_loop_stop=True)
        self._set_drive(None)

        for axw in self.axis_widgets:
            axw.configChanged.disconnect()
            axw.axis.terminate(delay_loop_stop=True)
            axw.axis = None
            axw.close()

        self.returnConfig.emit(config)

    def return_and_close(self):
        config = _deepcopy_dict(self.drive_config)

        self.logger.info(
            f"Drive has been validated and is being returned so it can be"
            f" added to the motion group.  Drive config is {config}."
        )
        self._safe_return_config_emit(config)
        self.close()

    def closeEvent(self, event):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                self.configChanged.disconnect()
        except RuntimeError:
            # everything already disconnected
            pass

        if isinstance(self.drive, Drive) and not self.drive.terminated:
            self.drive.terminate(delay_loop_stop=True)

        for axw in self.axis_widgets:
            axw.close()

        loop_safe_stop(self.drive_loop)

        super().closeEvent(event)
