__all__ = ["AxisConfigWidget", "DriveConfigOverlay"]

import asyncio
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
    QSizePolicy,
    QFrame,
    QVBoxLayout,
    QLineEdit,
)
from typing import Any, Dict, List, Union

from bapsf_motion.actors import Axis, Drive, MotionGroup
from bapsf_motion.gui.configure import motion_group_widget as mgw
from bapsf_motion.gui.configure.bases import _ConfigOverlay
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.widgets import (
    IPv4Validator,
    HLinePlain,
    LED,
    StyleButton,
)
from bapsf_motion.utils import ipv4_pattern, _deepcopy_dict, loop_safe_stop


class AxisConfigWidget(QWidget):
    configChanged = Signal()
    axis_loop = asyncio.new_event_loop()

    def __init__(self, name, parent=None):
        super().__init__(parent=parent)

        self._logger = logging.getLogger(f"{gui_logger.name}.ACW")
        self._ip_handlers = []

        self._axis_config = {
            "name": name,
            "units": "cm",
            "ip": "",
            "units_per_rev": "",
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
        self.cm_per_rev_widget = _widget

        # Define ADVANCED WIDGETS

        self.setStyleSheet(
            """
            AxisConfigWidget QLabel {
                border: 0px;
            }

            QLabel {padding: 0px}
            """
        )

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.ip_widget.editingFinished.connect(self._change_ip_address)
        self.cm_per_rev_widget.editingFinished.connect(self._change_cm_per_rev)

        self.configChanged.connect(self._update_ip_widget)
        self.configChanged.connect(self._update_cm_per_rev_widget)
        self.configChanged.connect(self._update_online_led)

    def _define_layout(self):
        _label = QLabel("IP:  ")
        _label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        ip_label = _label

        _label = QLabel("cm / rev")
        _label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        cm_per_rev_label = _label

        _label = QLabel("online")
        _label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter
        )
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(12)
        _label.setFont(font)
        online_label = _label

        sub_layout = QVBoxLayout()
        sub_layout.addWidget(online_label, alignment=Qt.AlignmentFlag.AlignBottom)
        sub_layout.addWidget(self.online_led, alignment=Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout()
        layout.addWidget(self.ax_name_widget)
        layout.addSpacing(12)
        layout.addWidget(ip_label)
        layout.addWidget(self.ip_widget)
        layout.addSpacing(32)
        layout.addWidget(self.cm_per_rev_widget)
        layout.addWidget(cm_per_rev_label)
        layout.addStretch()
        layout.addLayout(sub_layout)
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
        # TODO: this needs to be more robust
        axis_config = self.axis_config.copy()
        axis_config["ip"] = config["ip"]
        axis_config["units_per_rev"] = config["units_per_rev"]
        self._axis_config = axis_config

        self.configChanged.emit()
        self._check_axis_completeness()

    def _check_axis_completeness(self):
        if isinstance(self.axis, Axis):
            return False

        _completeness = {"name", "ip", "units", "units_per_rev"}
        if _completeness - set(self.axis_config.keys()):
            return False
        elif any([self.axis_config[key] == "" for key in _completeness]):
            return False

        self._spawn_axis()
        return True

    def _change_cm_per_rev(self):
        try:
            new_cpr = float(self.cm_per_rev_widget.text())
        except ValueError as err:
            self.logger.error(f"{err.__class__.__name__}: {err}")
            self.logger.error(f"Given cm / rev conversion must be a number.")
            self.configChanged.emit()
            return

        if self.axis is not None:
            self.axis.units_per_rev = new_cpr
        else:
            self.axis_config["units_per_rev"] = new_cpr

        self.configChanged.emit()
        self._check_axis_completeness()

    def _change_ip_address(self):
        new_ip = self.ip_widget.text()
        new_ip = self._validate_ip(new_ip)
        if new_ip is None:
            # ip was not valid
            self.configChanged.emit()
            return

        if self.axis is not None:
            config = self.axis_config
            config["ip"] = new_ip

            self.axis.terminate(delay_loop_stop=True)

            self._axis_config = config
            self.axis = None
        else:
            self.axis_config["ip"] = new_ip

        self.configChanged.emit()
        self._check_axis_completeness()

    def _spawn_axis(self) -> Union[Axis, None]:
        self.logger.info("Spawning Axis.")
        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)

        try:
            axis = Axis(
                **self.axis_config,
                logger=logging.getLogger(f"{self.logger.name}.AC"),
                loop=self.axis_loop,
                auto_run=True,
            )

            axis.motor.status_changed.connect(self._update_online_led)
        except ConnectionError:
            axis = None

        self.axis = axis
        return axis

    def _update_cm_per_rev_widget(self):
        self.cm_per_rev_widget.setText(f"{self.axis_config['units_per_rev']}")

    def _update_ip_widget(self):
        self.logger.info(f"Updating IP widget with {self.axis_config['ip']}")
        self.ip_widget.setText(self.axis_config["ip"])

    def _update_online_led(self):
        online = False

        if isinstance(self.axis, Axis):
            online = self.axis.motor.status["connected"]

        self.online_led.setChecked(online)

    def _validate_ip(self, ip):
        if ip == self.axis_config["ip"]:
            # ip did not change
            return ip
        elif ipv4_pattern.fullmatch(ip) is None:
            self.logger.error(
                f"Supplied IP address ({ip}) is not a valid IPv4."
            )
            return

        for handler in self._ip_handlers:
            ip = handler(ip)

            if ip is None or ip == "":
                return

        return ip

    def link_external_axis(self, axis):
        if not isinstance(axis, Axis):
            self.logger.warning(
                "NOT linking external axis, supplied axis is not an Axis object."
            )
            return

        self.logger.info(f"Linking external axis {axis.name}.")

        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)

        axis.motor.status_changed.connect(self._update_online_led)
        self.axis = axis

    def set_ip_handler(self, handler: callable):
        self._ip_handlers.append(handler)

    def closeEvent(self, event):
        self.logger.info("Closing AxisConfigWidget")

        try:
            self.configChanged.disconnect()
        except (RuntimeError, RuntimeWarning):
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

        _btn = StyleButton("Load a Default")
        _btn.setFixedWidth(250)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.load_default_btn = _btn

        _btn = StyleButton("Add Axis")
        _btn.setFixedWidth(120)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.add_axis_btn = _btn

        _btn = StyleButton("Validate")
        _btn.setFixedWidth(120)
        _btn.setFixedHeight(36)
        font = _btn.font()
        font.setPointSize(20)
        _btn.setFont(font)
        self.validate_btn = _btn

        _btn = LED()
        _btn.set_fixed_height(32)
        _btn.off_color = "d43729"
        self.validate_led = _btn

        # Define TEXT WIDGETS
        _widget = QLineEdit()
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        self.dr_name_widget = _widget

        # Define ADVANCED WIDGETS

        self.setLayout(self._define_layout())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connect_signals()

        _drive_config = None
        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            self.mg.drive.terminate(delay_loop_stop=True)
            _drive_config = _deepcopy_dict(self.mg.drive.config)
        elif not isinstance(parent, mgw.MGWidget):
            pass
        elif parent.drive_dropdown.currentText != "Custom Drive":
            index = parent.drive_dropdown.currentIndex()
            _drive_config = _deepcopy_dict(
                parent.drive_defaults[index][1]
            )
        elif "drive" in parent._initial_mg_config:
            _drive_config = _deepcopy_dict(parent._initial_mg_config["drive"])

        self.drive_config = _drive_config

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
        layout.addWidget(self._spawn_axis_widget("X"))
        layout.addWidget(self._spawn_axis_widget("Y"))
        layout.addStretch(1)

        return layout

    def _define_banner_layout(self):

        layout = QHBoxLayout()
        layout.addWidget(self.discard_btn)
        layout.addStretch()
        layout.addWidget(self.load_default_btn)
        layout.addStretch()
        layout.addWidget(self.done_btn)
        return layout

    def _define_second_row_layout(self):
        _label = QLabel("Drive Name:  ")
        _label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        _label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = _label.font()
        font.setPointSize(16)
        _label.setFont(font)
        _label.setStyleSheet("border: 0px")
        name_label = _label

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

        self._drive_config["axes"] = {}
        for ii, axw in enumerate(self.axis_widgets):
            self._drive_config["axes"][ii] = axw.axis_config

        return self._drive_config

    @drive_config.setter
    def drive_config(self, config):
        # TODO: this needs to be more robust...actually validate the config
        if config is None or not config:
            self._drive_config = None
            self.configChanged.emit()
            return
        # elif "name" not in config:
        #     self.logger.warning("Drive configuration does not supply a name.")
        #     return
        # elif "axes" not in config:
        #     self.logger.warning("Drive configuration does not define axes.")
        #     return
        # elif len(config["axes"]) != 2:
        #     self.logger.warning("Drive can only have 2 axes!!")
        # elif all(["ip" in ax_config for ax_config in config.values()]):
        #     ...

        try:
            self._spawn_drive(config)
        except (TypeError, ValueError, KeyError) as err:
            self.logger.warning(
                f"Given drive configuration is not valid, so doing nothing.",
                exc_info=err
            )
            self._drive_config = (
                None if "name" not in config else {"name": config["name"]}
            )
            self.configChanged.emit()

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

    def _change_drive_name(self):
        self.logger.info("Renaming drive...")
        new_name = self.dr_name_widget.text()
        if isinstance(self.drive, Drive):
            self.drive.name = new_name
        else:
            self.drive_config["name"] = new_name

        self.configChanged.emit()

    def _change_validation_state(self, validate=False):
        self.logger.info(f"Changing validation state to {validate}.")
        self.validate_led.setChecked(validate)
        self.done_btn.setEnabled(validate)

        if isinstance(self.drive, Drive) and not validate:
            config = {"name": self.drive.config.pop("name")}

            self.drive.terminate(delay_loop_stop=True)
            self._set_drive(None)

            self.drive_config = config

    def _update_dr_name_widget(self):
        self.dr_name_widget.setText(self.drive_config["name"])

    def set_drive_handler(self, handler: callable):
        ...

    def _validate_ip(self, ip):
        existing_ips = self.axis_ips
        if ip in existing_ips:
            self.logger.error(
                f"Supplied IP ({ip}) already exists amongst instantiated axes."
            )
            return

        return ip

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
            self.logger.warning(
                "Drive is not valid since not all axes are configured."
            )
            return
        elif not all([axw.online_led.isChecked() for axw in self.axis_widgets]):
            self.logger.warning(
                "Drive is not valid since not all axes are online."
            )
            return
        elif self.dr_name_widget.text() == "":
            self.logger.warning(
                "Drive is not valid, it needs a name."
            )
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
        _frame = QFrame()
        _frame.setLayout(QVBoxLayout())

        _widget = AxisConfigWidget(name, parent=self)
        _widget.set_ip_handler(self._validate_ip)
        _widget.configChanged.connect(self._change_validation_state)
        _widget.configChanged.connect(self._terminate_drive)
        # _widget.setStyleSheet(
        #     "border: 3px solid rgb(95, 95, 95);"
        #     "border-radius: 5px;"
        # )

        self.axis_widgets.append(_widget)

        _frame.layout().addWidget(_widget)
        _frame.setStyleSheet(
            "border: 3px solid rgb(95, 95, 95);"
            "border-radius: 5px;"
            "padding: 6px;"
        )

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

            for ii, ax in enumerate(drive.axes):
                self.axis_widgets[ii].link_external_axis(ax)

        except (ConnectionError, TimeoutError):
            self.logger.warning("Not able to instantiate Drive.")
            drive = None

            for axw in self.axis_widgets:
                axw.axis.run()

        self._set_drive(drive)

        return drive

    def _terminate_drive(self):
        if not isinstance(self.drive, Drive):
            return

        config = {"name": self.drive.config.pop("name")}

        self.drive.terminate(delay_loop_stop=True)
        self._set_drive(None)

        self.drive_config = config

    def return_and_close(self):
        config = _deepcopy_dict(self.drive_config)

        self.configChanged.disconnect()
        self.drive.terminate(delay_loop_stop=True)
        self._set_drive(None)

        for axw in self.axis_widgets:
            axw.configChanged.disconnect()
            axw.axis.terminate(delay_loop_stop=True)
            axw.axis = None
            axw.close()

        self.logger.info(
            f"Drive has been validated and is being returned so it can be"
            f" added to the motion group.  Drive config is {config}."
        )
        self.returnConfig.emit(config)
        self.close()

    def closeEvent(self, event):
        try:
            self.configChanged.disconnect()
        except (RuntimeError, RuntimeWarning):
            # everything already disconnected
            pass

        if isinstance(self.drive, Drive) and not self.drive.terminated:
            self.drive.terminate(delay_loop_stop=True)

        for axw in self.axis_widgets:
            axw.close()

        loop_safe_stop(self.drive_loop)

        super().closeEvent(event)
