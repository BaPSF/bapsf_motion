"""
This module defines the configuration GUI for construction data runs.
"""
__all__ = ["ConfigureGUI"]

import ast
import asyncio
import inspect
import logging
import logging.config
import matplotlib as mpl
import numpy as np
import re

from abc import abstractmethod
from pathlib import Path
from PySide6.QtCore import (
    Qt,
    QDir,
    Signal,
    Slot,
    QSize,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QPainter,
    QIcon,
    QDoubleValidator,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QFrame,
    QTextEdit,
    QListWidget,
    QVBoxLayout,
    QLineEdit,
    QFileDialog,
    QStackedWidget,
    QComboBox,
)
from typing import Any, Dict, List, Union, Optional

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.actors import (
    RunManager,
    RunManagerConfig,
    MotionGroup,
    MotionGroupConfig,
    Drive,
    Axis,
)
from bapsf_motion.gui.widgets import (
    QLogger,
    StyleButton,
    LED,
    QLineEditSpecialized,
    HLinePlain,
    VLinePlain,
    IPv4Validator,
)
from bapsf_motion.motion_builder import MotionBuilder
from bapsf_motion.motion_builder.layers import layer_registry
from bapsf_motion.motion_builder.exclusions import exclusion_registry
from bapsf_motion.transform import BaseTransform
from bapsf_motion.transform.helpers import transform_registry, transform_factory
from bapsf_motion.utils import toml, ipv4_pattern, _deepcopy_dict
from bapsf_motion.utils import units as u


# noqa
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa

_logger = logging.getLogger("GUI")


class _OverlayWidget(QWidget):
    closing = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

        # make the window frameless
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("_OverlayWidget{ border: 2px solid black }")

        self.background_fill_color = QColor(30, 30, 30, 120)
        self.background_pen_color = QColor(30, 30, 30, 120)

        self.overlay_fill_color = QColor(50, 50, 50)
        self.overlay_pen_color = QColor(90, 90, 90)

        self._margins = [0.01, 0.01]  # [ w_margin / width, h_margin / height]
        self._set_contents_margins(*self._margins)

    def _set_contents_margins(self, width_fraction, height_fraction):
        width = int(width_fraction * self.parent().width())
        height = int(height_fraction * self.parent().height())

        self.setContentsMargins(width, height, width, height)

    def paintEvent(self, event):
        # This method is, in practice, drawing the contents of
        # your window.

        # get current window size
        s = self.parent().size()
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        qp.setPen(self.background_pen_color)
        qp.setBrush(self.background_fill_color)
        qp.drawRoundedRect(0, 0, s.width(), s.height(), 3, 3)

        # draw overlay
        qp.setPen(self.overlay_pen_color)
        qp.setBrush(self.overlay_fill_color)

        self.contentsRect().width()
        ow = int((s.width() - self.contentsRect().width()) / 2)
        oh = int((s.height() - self.contentsRect().height()) / 2)
        qp.drawRoundedRect(
            ow,
            oh,
            self.contentsRect().width(),
            self.contentsRect().height(),
            5,
            5,
        )

        qp.end()

    def closeEvent(self, event):
        self.closing.emit()
        event.accept()


class _ConfigOverlay(_OverlayWidget):
    configChanged = Signal()
    returnConfig = Signal(object)

    def __init__(self, mg: MotionGroup, parent: "MGWidget" = None):
        super().__init__(parent=parent)

        self._logger = _logger
        self._mg = mg

        # Define BUTTONS

        _btn = StyleButton("Add / Update", parent=self)
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = StyleButton("Discard", parent=self)
        _btn.setFixedWidth(250)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        font.setBold(True)
        _btn.setFont(font)
        _btn.update_style_sheet(
            {"background-color": "rgb(255, 110, 110)"}
        )
        self.discard_btn = _btn

    def _connect_signals(self):
        self.discard_btn.clicked.connect(self.close)
        self.done_btn.clicked.connect(self.return_and_close)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def mg(self) -> Union[MotionGroup, None]:
        """Working motion group."""
        return self._mg

    @abstractmethod
    def return_and_close(self):
        ...

    def closeEvent(self, event):
        self.logger.info(f"Closing {self.__class__.__name__}")
        super().closeEvent(event)


class AxisConfigWidget(QWidget):
    configChanged = Signal()
    axis_loop = asyncio.new_event_loop()

    def __init__(self, name, parent=None):
        super().__init__(parent=parent)

        self._logger = _logger
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
                logger=self.logger,
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
        except RuntimeError:
            # everything already disconnected
            pass

        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)

        self.axis_loop.call_soon_threadsafe(self.axis_loop.stop)

        event.accept()


class DriveConfigOverlay(_ConfigOverlay):
    drive_loop = asyncio.new_event_loop()

    def __init__(self, mg: MotionGroup, parent: "MGWidget" = None):
        super().__init__(mg, parent)

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

        if isinstance(self.mg, MotionGroup) and isinstance(self.mg.drive, Drive):
            self.mg.drive.terminate(delay_loop_stop=True)
            self.drive_config = _deepcopy_dict(self.mg.drive.config)

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
                logger=self.logger,
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
        config = self.drive_config

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
        except RuntimeError:
            # everything already disconnected
            pass

        for axw in self.axis_widgets:
            axw.close()

        if isinstance(self.drive, Drive):
            self.drive.terminate(delay_loop_stop=True)

        self.drive_loop.call_soon_threadsafe(self.drive_loop.stop)

        super().closeEvent(event)


class TransformConfigOverlay(_ConfigOverlay):
    registry = transform_registry

    def __init__(self, mg: MotionGroup, parent: "MGWidget" = None):
        super().__init__(mg, parent)

        self._transform = None
        self._params_widget = None  # type: Union[None, QWidget]
        self._transform_inputs = None

        # Define BUTTONS
        # Define TEXT WIDGETS
        # Define ADVANCED WIDGETS
        _w = QComboBox(self)
        _w.setMinimumWidth(300)
        _w.setMaximumWidth(500)
        _w.addItems(
            list(self.registry.get_names_by_dimensionality(self._mg.drive.naxes))
        )
        _w.setEditable(False)
        _w.setCurrentText(self._mg.transform.transform_type)
        font = _w.font()
        font.setPointSize(18)
        _w.setFont(font)
        self.combo_widget = _w

        self.setLayout(self._define_layout())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()

        self.combo_widget.currentTextChanged.connect(self._refresh_params_widget)

    def _define_layout(self):

        self._params_widget = self._define_params_widget(
            self.transform.transform_type
        )

        layout = QVBoxLayout()
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(8)
        layout.addWidget(self.combo_widget)
        layout.addSpacing(8)
        layout.addWidget(self._params_widget)
        layout.addStretch()

        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(
            self.discard_btn,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch()
        layout.addWidget(
            self.done_btn,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        return layout

    @property
    def transform(self) -> BaseTransform:
        """
        The transform object that been constructed for :attr:`mg`.
        """
        if self._transform is None:
            return self.mg.transform

        return self._transform

    @property
    def transform_inputs(self) -> Dict[str, Any]:
        """
        Dictionary of input values for creating the :attr:`transform`
        instance.
        """
        if self._transform_inputs is None:
            self._transform_inputs = {}

        return self._transform_inputs

    @property
    def transform_type(self):
        return self.combo_widget.currentText()

    def _define_params_widget(self, tr_type: str):
        # re-initialized the transform_inputs dictionary
        params = self.registry.get_input_parameters(tr_type)
        if self.transform.transform_type == tr_type:
            self._transform_inputs = {**self.transform.config}
            self._transform_inputs.pop("type")
        else:
            self._transform_inputs = {}

        _widget = QWidget(parent=self)
        layout = QGridLayout(_widget)
        layout.setSpacing(4)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 4)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)

        ii = 0
        for key, val in params.items():
            # determine the seeded value for the transform input
            if key in self.transform_inputs:
                default = self.transform_inputs[key]
            elif val["param"].default is not val["param"].empty:
                default = val["param"].default
                self.transform_inputs[key] = default
            else:
                default = None
                self.transform_inputs[key] = default

            _txt = QLabel(key, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _label = _txt

            annotation = val['param'].annotation
            if inspect.isclass(annotation):
                annotation = annotation.__name__
            annotation = f"{annotation}".split(".")[-1]

            _txt = QLabel(annotation, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _type = _txt

            text = "" if default is None else f"{default}"
            _txt = QLineEditSpecialized(text, parent=_widget)
            _txt.setObjectName(key)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            font = _txt.font()
            font.setPointSize(16)
            _txt.setFont(font)
            _input = _txt
            _input.editingFinishedPayload.connect(self._update_transform_inputs)

            _txt = QLabel("", parent=_widget)
            _icon = qta.icon("fa.question-circle-o").pixmap(QSize(16, 16))  # type: QIcon
            _txt.setPixmap(_icon)
            _txt.setToolTip("\n".join(val["desc"]))
            _txt.setToolTipDuration(5000)
            _help = _txt

            layout.addWidget(_label, ii, 0, alignment=Qt.AlignmentFlag.AlignRight)
            layout.addWidget(_type, ii, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(_input, ii, 2, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(_help, ii, 3, alignment=Qt.AlignmentFlag.AlignLeft)
            ii += 1

        return _widget

    @Slot(str)
    def _refresh_params_widget(self, tr_type):
        _widget = self._define_params_widget(tr_type)

        old_widget = self._params_widget
        self.layout().replaceWidget(old_widget, _widget)
        self._params_widget = _widget

        old_widget.close()
        old_widget.deleteLater()

        self._validate_inputs()

    @Slot(object)
    def _update_transform_inputs(self, input_widget: "QLineEditSpecialized"):
        param = input_widget.objectName()
        _input_string = input_widget.text()

        try:
            _input = ast.literal_eval(_input_string)
        except (ValueError, SyntaxError):
            params = self.registry.get_input_parameters(self.transform_type)
            _type = params[param]["param"].annotation
            if inspect.isclass(_type) and issubclass(_type, str):
                _input = _input_string
            elif _input_string == "":
                _input = None
            else:
                self.logger.exception(
                    f"Input '{input_widget.text()}' is not a valid type for '{param}'."
                )
                _input = None
                input_widget.setText("")
                raise

        self.transform_inputs[param] = _input

        self.logger.info(
            f"Updating input parameter {param} to {_input} for transformation "
            f"type {self.transform_type}."
        )

        self._validate_inputs()

    def _validate_inputs(self):
        tr_type = self.transform_type
        _inputs = self.transform_inputs
        params = self.registry.get_input_parameters(tr_type)

        for key, val in _inputs.items():
            annotation = params[key]["param"]

            if val is not None:
                continue
            elif (
                annotation is None
                or (
                    hasattr(annotation, "__args__")
                    and type(None) in annotation.__args__
                )
            ):
                # val is None and is allowed to be None
                continue
            else:
                # not all inputs have been defined yet
                self.change_validation_state(False)
                return

        try:
            transform = transform_factory(
                self.mg.drive, tr_type=self.transform_type, **self.transform_inputs
            )
            self._transform = transform
            self.change_validation_state(True)
        except (ValueError, TypeError):
            self.logger.exception("Supplied transform input arguments are not valid.")
            self.change_validation_state(False)
            raise

    def change_validation_state(self, valid: bool = False):
        self.done_btn.setEnabled(valid)

    def return_and_close(self):
        config = self.transform.config

        self.logger.info(
            f"New transform configuration of type {config['type']} is "
            f"being returned."
        )
        self.returnConfig.emit(config)
        self.close()


class MotionBuilderConfigOverlay(_ConfigOverlay):
    layer_registry = layer_registry
    exclusion_registry = exclusion_registry

    def __init__(self, mg: MotionGroup, parent: "MGWidget" = None):
        super().__init__(mg, parent)

        self._mb = None

        self._space_input_widgets = {}  # type: Dict[str, Dict[str, QLineEditSpecialized]]

        # _param_inputs:
        #     dictionary of input parameters for instantiating an exclusion or
        #     points layer
        # _params_widget:
        #     top enclosing widget for setting and configuring parameter inputs
        #     for an exclusion or point layer
        # _params_field_widget:
        #     child widget of _params_widget that contains the actual inpu fields
        #     for configuring _param_inputs
        # _params_input_widgets:
        #     dictionary of the actual widgets that control the _param_inputs
        #     values
        self._param_inputs = {}  # type: Dict[str, Anay]
        self._params_widget = None  # type: Union[QWidget, None]
        self._params_field_widget = None  # type: Union[QWidget, None]
        self._params_input_widgets = {}  # type: Dict[str, Dict[str, QLineEditSpecialized]]

        # Define BUTTONS

        self.add_ly_btn = self._generate_btn_widget("ADD")
        self.remove_ly_btn = self._generate_btn_widget("REMOVE")
        self.remove_ly_btn.setEnabled(False)
        self.edit_ly_btn = self._generate_btn_widget("EDIT")
        self.edit_ly_btn.setEnabled(False)

        self.add_ex_btn = self._generate_btn_widget("ADD")
        self.remove_ex_btn = self._generate_btn_widget("REMOVE")
        self.remove_ex_btn.setEnabled(False)
        self.edit_ex_btn = self._generate_btn_widget("EDIT")
        self.edit_ex_btn.setEnabled(False)

        self.params_add_btn = self._generate_btn_widget("Add / Update")
        self.params_discard_btn = self._generate_btn_widget("Discard")

        # Define TEXT WIDGETS
        _txt = QComboBox(parent=self)
        _txt.setMinimumWidth(200)
        _txt.setMaximumWidth(400)
        _txt.setEditable(False)
        # _txt.addItems(_available)
        # _txt.setCurrentText(_type)
        self.params_combo_box = _txt

        _txt = QLabel("", parent=self)
        self.params_label = _txt

        # Define ADVANCED WIDGETS

        self.layer_list_box = QListWidget(parent=self)
        self.layer_list_box.setMinimumHeight(250)
        self.exclusion_list_box = QListWidget(parent=self)
        self.exclusion_list_box.setMinimumHeight(250)

        self.mpl_canvas = FigureCanvas()
        self.mpl_canvas.setParent(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._initialize_motion_builder()
        self.setLayout(self._define_layout())

        self.update_exclusion_list_box()
        self.update_layer_list_box()
        self.update_canvas()

        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()

        self.configChanged.connect(self.update_canvas)
        self.configChanged.connect(self.update_exclusion_list_box)
        self.configChanged.connect(self.update_layer_list_box)
        self.configChanged.connect(self._validate_mb)

        self.add_ex_btn.clicked.connect(self._exclusion_configure_new)
        self.remove_ex_btn.clicked.connect(self._exclusion_remove_from_mb)
        self.edit_ex_btn.clicked.connect(self._exclusion_modify_existing)

        self.add_ly_btn.clicked.connect(self._layer_configure_new)
        self.remove_ly_btn.clicked.connect(self._layer_remove_from_mb)
        self.edit_ly_btn.clicked.connect(self._layer_modify_existing)

        self.params_discard_btn.clicked.connect(self._hide_and_clear_params_widget)
        self.params_add_btn.clicked.connect(self._add_to_mb)

        self.params_combo_box.currentTextChanged.connect(
            self._refresh_params_widget_from_combo_box_change
        )

        self.layer_list_box.itemSelectionChanged.connect(
            self.layer_list_box_set_btn_enable
        )
        self.exclusion_list_box.itemSelectionChanged.connect(
            self.exclusion_list_box_set_btn_enable
        )

    def _define_layout(self):
        #
        #  +-------------------------------------------------------+
        #  | banner_layout                                         |
        #  +-------------------+-----------------------------------+
        #  |     sidebar       | right_area                        |
        #  |                   |                                   |
        #  | +--------------+  |  +-----------------------------+  |
        #  | | motion_space |  |  | Plot                        |  |
        #  | |              |  |  |                             |  |
        #  | +--------------+  |  |                             |  |
        #  |                   |  |                             |  |
        #  | +--------------+  |  +-----------------------------+  |
        #  | |  exclusion   |  |                                   |
        #  | |  list        |  |  +--params_widget--------------+  |
        #  | +--------------+  |  |                             |  |
        #  |                   |  | banner                      |  |
        #  | +--------------+  |  |                             |  |
        #  | |  layer       |  |  | +--params_field_widget----+ |  |
        #  | |  list        |  |  | |                         | |  |
        #  | +--------------+  |  | +-------------------------+ |  |
        #  |                   |  +-----------------------------+  |
        #  +-------------------+-----------------------------------+
        #
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(0)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.addWidget(self._define_sidebar_widget())
        sub_layout.addSpacing(8)
        sub_layout.addWidget(VLinePlain(parent=self))
        sub_layout.addWidget(self._define_right_area_widget())

        layout = QVBoxLayout()
        layout.setSpacing(12)

        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(6)
        layout.addLayout(sub_layout)

        return layout

    @property
    def dimensionality(self):
        return self.mg.drive.naxes

    @property
    def axis_names(self):
        return self.mg.drive.anames

    @property
    def mb(self) -> Union[MotionBuilder, None]:
        if (
            self._mb is None
            and isinstance(self.mg, MotionGroup)
            and isinstance(self.mg.mb, MotionBuilder)
        ):
            return self.mg.mb

        return self._mb

    # -- LAYOUT AND WIDGET DEFINITIONS --

    def _define_banner_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(
            self.discard_btn,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch()
        layout.addWidget(
            self.done_btn,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        return layout

    def _define_sidebar_widget(self):
        _widget = QWidget(parent=self)
        _widget.setMinimumWidth(350)
        _widget.setMaximumWidth(500)
        _widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        layout.addLayout(self._define_motion_space_layout())
        layout.addSpacing(20)
        layout.addLayout(self._define_exclusion_list_layout())
        layout.addSpacing(24)
        layout.addLayout(self._define_layer_list_layout())
        layout.addStretch()

        return _widget

    def _define_right_area_widget(self):
        _widget = QWidget(parent=self)
        _widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(_widget)
        layout.addWidget(self.mpl_canvas)
        layout.addWidget(HLinePlain(parent=self))
        layout.addWidget(self._define_params_widget())

        return _widget

    def _define_motion_space_layout(self):

        _txt = QLabel("Motion Space", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)

        layout = QGridLayout()
        layout.setContentsMargins(8, 4, 12, 4)
        layout.setSpacing(4)
        layout.setColumnMinimumWidth(4, 18)
        layout.setRowMinimumHeight(1, 12)
        layout.addWidget(
            _txt, 0, 0, 1, 8,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
        )

        for ii, args in self.mb.config["space"].items():
            axis = self.mg.drive.axes[ii]
            name = args["label"]

            _txt = QLabel(name, parent=self)
            font = _txt.font()
            font.setPointSize(12)
            _txt.setFont(font)
            axis_label = _txt

            _txt = QLabel("range", parent=self)
            _txt.setFont(font)
            range_label = _txt

            _txt = QLineEditSpecialized(f"{args['range'][0]:.2f}", parent=self)
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_min")
            _txt.setValidator(QDoubleValidator(decimals=1))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            min_range = _txt

            _txt = QLineEditSpecialized(f"{args['range'][1]:.2f}", parent=self)
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_max")
            _txt.setValidator(QDoubleValidator(decimals=1))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            max_range = _txt

            _txt = QLabel("Δ", parent=self)
            _txt.setFont(font)
            delta_label = _txt

            _txt = QLineEditSpecialized(
                f"{(args['range'][1] - args['range'][0]) / args['num']:.2f}",
                parent=self
            )
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_delta")
            _txt.setValidator(QDoubleValidator(decimals=2))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            delta = _txt

            _txt = QLabel(f"{axis.units}", parent=self)
            _txt.setFont(font)
            unit_label = _txt

            layout.addWidget(
                axis_label, ii + 2, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            layout.addWidget(
                range_label, ii + 2, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                min_range, ii + 2, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                max_range, ii + 2, 3, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                delta_label, ii + 2, 5, 1, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            layout.addWidget(
                delta, ii + 2, 6, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                unit_label, ii + 2, 7, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft
            )

            self._space_input_widgets[name] = {
                "min": min_range,
                "max": max_range,
                "delta": delta,
            }

        return layout

    def _define_exclusion_list_layout(self):

        _txt = QLabel("Exclusion Layers", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)
        title = _txt

        ex_types = set(ex.exclusion_type for ex in self.mb.exclusions)

        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        ex_names = []
        if not _available:
            self.logger.warning(
                "There are no coded exclusion layers that work with the "
                f"dimensionality of the existing probe drive, {self.dimensionality}."
            )
            self.add_ex_btn.setEnabled(False)
            self.remove_ex_btn.setEnabled(False)
            self.edit_ex_btn.setEnabled(False)

            exclusions = self.mb.exclusions.copy()
            for ex in exclusions:
                self.mb.remove_exclusion(ex.name)

        elif ex_types - _available:
            exclusions = self.mb.exclusions.copy()
            for ex in exclusions:
                if ex.exclusion_type in _available:
                    ex_names.append(
                        self._generate_list_name(ex.name, ex.exclusion_type)
                    )
                    continue

                self.mb.remove_exclusion(ex.name)

        self.exclusion_list_box.addItems(ex_names)

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(8)
        sub_layout.addWidget(self.add_ex_btn)
        sub_layout.addWidget(self.remove_ex_btn)
        sub_layout.addWidget(self.edit_ex_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            title,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addSpacing(2)
        layout.addWidget(self.exclusion_list_box)
        layout.addLayout(sub_layout)

        return layout

    def _define_layer_list_layout(self):

        _txt = QLabel("Point Layers", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)
        title = _txt

        ly_types = set(ly.layer_type for ly in self.mb.layers)

        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        ly_names = []
        if not _available:
            self.logger.warning(
                "There are no coded point layers that work with the "
                f"dimensionality of the existing probe drive, {self.dimensionality}."
            )
            self.add_ly_btn.setEnabled(False)
            self.remove_ly_btn.setEnabled(False)
            self.edit_ly_btn.setEnabled(False)

            layers = self.mb.layers.copy()
            for ly in layers:
                self.mb.remove_layer(ly.name)

        elif ly_types - _available:
            layers = self.mb.layers.copy()
            for ly in layers:
                if ly.layer_type in _available:
                    ly_names.append(
                        self._generate_list_name(ly.name, ly.layer_type)
                    )
                    continue

                self.mb.remove_layer(ly.name)

        self.layer_list_box.addItems(ly_names)

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(8)
        sub_layout.addWidget(self.add_ly_btn)
        sub_layout.addWidget(self.remove_ly_btn)
        sub_layout.addWidget(self.edit_ly_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            title,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addSpacing(2)
        layout.addWidget(self.layer_list_box)
        layout.addLayout(sub_layout)

        return layout

    def _define_plot_layout(self):
        ...

    def _define_params_widget(self):
        _widget = QWidget(parent=self)
        _widget.setMinimumHeight(300)
        size_policy = _widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        _widget.setSizePolicy(size_policy)
        layout = QVBoxLayout(_widget)

        self.params_add_btn.setEnabled(False)

        hline = HLinePlain(parent=self)
        hline.set_color(30, 30, 30)
        hline.setLineWidth(2)

        self._params_field_widget = QWidget(parent=_widget)

        banner_layout = QHBoxLayout()
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.setSpacing(8)

        banner_layout.addWidget(
            self.params_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        banner_layout.addSpacing(20)
        banner_layout.addWidget(
            self.params_combo_box,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        banner_layout.addStretch()
        banner_layout.addWidget(
            self.params_discard_btn,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        banner_layout.addWidget(
            self.params_add_btn,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )

        layout.addLayout(banner_layout)
        layout.addWidget(hline)
        layout.addWidget(self._params_field_widget)
        layout.addStretch()

        self._params_widget = _widget
        self._params_widget.hide()
        return self._params_widget

    def _define_params_field_widget(self, ex_or_ly, _type):
        _registry = (
            self.exclusion_registry
            if ex_or_ly == "exclusion"
            else self.layer_registry
        )

        self._param_inputs.update(
            {"_type": _type, "_registry": _registry}
        )

        params = _registry.get_input_parameters(_type)

        _widget = QWidget(parent=self._params_widget)
        layout = QGridLayout(_widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # layout.setColumnStretch(0, 2)
        # layout.setColumnStretch(1, 2)
        # layout.setColumnStretch(2, 4)
        # layout.setColumnStretch(3, 1)
        # layout.setColumnStretch(4, 1)

        ii = 0
        for key, val in params.items():
            # determine the seeded value for the transform input
            if key in self._param_inputs:
                default = self._param_inputs[key]
            elif val["param"].default is not val["param"].empty:
                default = val["param"].default
                self._param_inputs[key] = default
            else:
                default = None
                self._param_inputs[key] = default

            _txt = QLabel(key, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _label = _txt

            annotation = val['param'].annotation
            if inspect.isclass(annotation):
                annotation = annotation.__name__
            annotation = f"{annotation}".split(".")[-1]

            _txt = QLabel(annotation, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _type = _txt

            text = "" if default is None else f"{default}"
            _txt = QLineEditSpecialized(text, parent=_widget)
            _txt.setObjectName(key)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            font = _txt.font()
            font.setPointSize(16)
            _txt.setFont(font)
            _input = _txt
            _input.editingFinishedPayload.connect(self._update_param_inputs)

            _txt = QLabel("", parent=_widget)
            _icon = qta.icon("fa.question-circle-o").pixmap(QSize(16, 16))  # type: QIcon
            _txt.setPixmap(_icon)
            _txt.setToolTip("\n".join(val["desc"]))
            _txt.setToolTipDuration(10000)
            _txt.setMaximumWidth(24)
            _help = _txt

            layout.addWidget(_label, ii, 0, alignment=Qt.AlignmentFlag.AlignRight)
            layout.addWidget(_type, ii, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(_input, ii, 2, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(_help, ii, 3, alignment=Qt.AlignmentFlag.AlignLeft)
            ii += 1

        return _widget

    # -- WIDGET INTERACTION FUNCTIONALITY --

    def _exclusion_configure_new(self):
        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText("New Exclusion")

        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available)
        self.params_combo_box.setObjectName("exclusion")

        self._refresh_params_widget()
        self._show_params_widget()

    def _exclusion_modify_existing(self):
        item = self.exclusion_list_box.currentItem()
        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        ex = None
        for _ex in self.mb.exclusions:
            if _ex.name == name:
                ex = _ex
                break
        if ex is None:
            return

        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText(ex.name)
        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available, ex.exclusion_type)
        self.params_combo_box.setObjectName("exclusion")

        self._param_inputs = ex.config.copy()
        self._param_inputs.pop("type")

        self._refresh_params_widget()
        self._show_params_widget()

    def _exclusion_remove_from_mb(self):
        ex_row = self.exclusion_list_box.currentRow()
        ex = self.exclusion_list_box.takeItem(ex_row)

        name = self._get_layer_name_from_list_name(ex.text())
        if name is None:
            return

        self.mb.remove_exclusion(name)
        # ex.deleteLater()

        # TODO: remove params_widget if the removed exclusion is currently
        #       populating the params_widget

        self.configChanged.emit()

    def _hide_and_clear_params_widget(self):
        self._params_field_widget.setEnabled(False)
        self._params_widget.hide()
        self._param_inputs = {}

    def _layer_configure_new(self):
        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText("New Layer")

        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available)
        self.params_combo_box.setObjectName("layer")

        self._refresh_params_widget()
        self._show_params_widget()

    def _layer_modify_existing(self):
        item = self.layer_list_box.currentItem()
        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        ly = None
        for _ly in self.mb.layers:
            if _ly.name == name:
                ly = _ly
                break
        if ly is None:
            return

        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText(ly.name)
        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available, ly.layer_type)
        self.params_combo_box.setObjectName("layer")

        self._param_inputs = ly.config.copy()
        self._param_inputs.pop("type")

        self._refresh_params_widget()
        self._show_params_widget()

    def _layer_remove_from_mb(self):
        ly_row = self.layer_list_box.currentRow()
        item = self.layer_list_box.takeItem(ly_row)

        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        self.logger.info(f"Removing layer {name}.")
        self.mb.remove_layer(name)
        # ex.deleteLater()

        # TODO: remove params_widget if the removed exclusion is currently
        #       populating the params_widget

        self.configChanged.emit()

    def _refresh_params_combo_box(self, items, current: Optional[str] = None):
        self.params_combo_box.currentTextChanged.disconnect()

        self.params_combo_box.setObjectName("")
        self.params_combo_box.clear()
        self.params_combo_box.addItems(items)
        if current is None:
            self.params_combo_box.setCurrentIndex(0)
        else:
            self.params_combo_box.setCurrentText(current)

        self.params_combo_box.currentTextChanged.connect(
            self._refresh_params_widget_from_combo_box_change
        )

    def _refresh_params_widget(self):
        self.params_add_btn.setEnabled(False)

        _type = self.params_combo_box.currentText()
        ex_or_ly = self.params_combo_box.objectName()

        _widget = self._define_params_field_widget(ex_or_ly, _type)

        old_widget = self._params_field_widget
        self._params_widget.layout().replaceWidget(old_widget, _widget)
        self._params_field_widget = _widget

        old_widget.close()
        old_widget.deleteLater()

        self._validate_inputs()

    def _refresh_params_widget_from_combo_box_change(self):
        self._param_inputs = {}
        self._refresh_params_widget()

    def _show_params_widget(self):
        self._params_field_widget.setEnabled(True)
        self._params_widget.show()

    @Slot(object)
    def _update_param_inputs(self, input_widget: "QLineEditSpecialized"):
        param = input_widget.objectName()
        _input_string = input_widget.text()

        _type = self._param_inputs["_type"]
        _registry = self._param_inputs["_registry"]

        try:
            _input = ast.literal_eval(_input_string)
        except (ValueError, SyntaxError):
            params = _registry.get_input_parameters(_type)
            _type = params[param]["param"].annotation
            if inspect.isclass(_type) and issubclass(_type, str):
                _input = _input_string
            elif _input_string == "":
                _input = None
            else:
                self.logger.exception(
                    f"Input '{input_widget.text()}' is not a valid type for '{param}'."
                )
                _input = None
                input_widget.setText("")
                raise

        self._param_inputs[param] = _input

        self.logger.info(
            f"Updating input parameter {param} to {_input} for transformation "
            f"type {_type}."
        )

        self._validate_inputs()

    @Slot(object)
    def _validate_space_inputs(self, input_widget: QLineEditSpecialized):
        self.logger.info("Validating space inputs")
        w_name = input_widget.objectName()
        match = re.compile(r"(?P<label>.+)_(?P<what>(min|max|delta))").fullmatch(w_name)
        if match is None:
            # input_widget does not have a name corresponding to the space inputs
            return

        axis_index = None
        axis_config = None
        axis_label = match.group("label")
        axis_input_type = match.group("what")

        space_config = self.mb.config["space"].copy()
        for key, value in space_config.items():
            if value["label"] == axis_label:
                axis_index = key
                axis_config = value
                break

        if axis_config is None:
            # This should never happen
            return None

        if axis_input_type == "delta":
            old_val = (
                    (axis_config["range"][1] - axis_config["range"][0])
                    / axis_config["num"]
            )
        else:
            old_val = (
                axis_config["range"][0]
                if axis_input_type == "min"
                else axis_config["range"][0]
            )

        try:
            new_val = float(input_widget.text())
            new_val_good = True
        except ValueError:
            new_val = None
            new_val_good = False

        range_window = axis_config["range"][1] - axis_config["range"][0]
        old_delta = range_window / axis_config["num"]

        if not new_val_good:
            pass
        elif axis_input_type == "min" and new_val >= axis_config["range"][1]:
            new_val_good = False
        elif axis_input_type == "min" and (
                old_delta / (axis_config["range"][1] - new_val) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "min":
            axis_config["range"][0] = new_val
            axis_config["num"] = int(
                np.ceil(
                    (axis_config["range"][1] - new_val) / old_delta
                )
            )
        elif axis_input_type == "max" and new_val <= axis_config["range"][0]:
            new_val_good = False
        elif axis_input_type == "max" and (
                old_delta / (new_val - axis_config["range"][0]) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "max":
            axis_config["range"][1] = new_val
            axis_config["num"] = int(
                np.ceil(
                    (new_val - axis_config["range"][0]) / old_delta
                )
            )
        elif axis_input_type == "delta" and (
                new_val / (axis_config["range"][1] - axis_config["range"][0]) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "delta":
            num = int(
                np.ceil(
                    (axis_config["range"][1] - axis_config["range"][0]) / new_val
                )
            )
            axis_config["num"] = num

        if not new_val_good:
            input_widget.setText(f"{old_val:.3f}")
            return

        space_config[axis_index] = axis_config
        config = {
            "space": space_config,
            "exclusion": self.mb.config.get("exclusion", None),
            "layer": self.mb.config.get("layer", None),
        }
        self._spawn_motion_builder(config)

    def _validate_inputs(self):
        self.logger.info("Validating motion layer parameter inputs")
        _inputs = self._param_inputs.copy()
        _type = _inputs.pop("_type")
        _registry = _inputs.pop("_registry")
        params = _registry.get_input_parameters(_type)

        for key, val in _inputs.items():
            annotation = params[key]["param"]

            if val is not None:
                continue
            elif (
                annotation is None
                or (
                    hasattr(annotation, "__args__")
                    and type(None) in annotation.__args__
                )
            ):
                # val is None and is allowed to be None
                continue
            else:
                # not all inputs have been defined yet
                self.change_validation_state(False)
                return

        try:
            _layer = _registry.factory(
                self.mb._ds,
                _type=_type,
                skip_ds_add=True,
                **_inputs,
            )
            # self._transform = transform
            self.change_validation_state(True)
        except (ValueError, TypeError):
            self.logger.exception("Supplied input arguments are not valid.")
            self.change_validation_state(False)
            raise

    def change_validation_state(self, valid: bool = False):
        self.params_add_btn.setEnabled(valid)

    def exclusion_list_box_set_btn_enable(self, enable=True):
        self.edit_ex_btn.setEnabled(enable)
        self.remove_ex_btn.setEnabled(enable)

    def layer_list_box_set_btn_enable(self, enable=True):
        self.edit_ly_btn.setEnabled(enable)
        self.remove_ly_btn.setEnabled(enable)

    def update_canvas(self):
        self.logger.info("Redrawing plot...")
        self.logger.info(f"MB config = {self.mb.config}")

        self.mpl_canvas.figure.clear()
        ax = self.mpl_canvas.figure.add_subplot(111)
        self.mb.mask.plot(
            x=self.mb.mask.dims[0],
            y=self.mb.mask.dims[1],
            ax=ax,
        )

        pts = self.mb.motion_list
        if pts is not None:
            ax.scatter(
                x=pts[..., 0],
                y=pts[..., 1],
                linewidth=1,
                s=2 ** 2,
                facecolors="deepskyblue",
                edgecolors="black",
            )

        self.mpl_canvas.draw()

    def update_exclusion_list_box(self):
        self.logger.info("Updating Exclusion List Box")
        self.remove_ex_btn.setEnabled(False)
        self.edit_ex_btn.setEnabled(False)

        ex_names = set(
            self._generate_list_name(ex.name, ex.exclusion_type)
            for ex in self.mb.exclusions
        )
        self.exclusion_list_box.clear()

        if not ex_names:
            return

        self.exclusion_list_box.addItems(ex_names)

    def update_layer_list_box(self):
        self.logger.info("Updating Layer List Box")
        self.remove_ly_btn.setEnabled(False)
        self.edit_ly_btn.setEnabled(False)

        ly_names = set(
            self._generate_list_name(ly.name, ly.layer_type)
            for ly in self.mb.layers
        )

        self.layer_list_box.clear()

        if not ly_names:
            return

        self.layer_list_box.addItems(ly_names)

    # -- NORMAL METHODS --

    def _add_to_mb(self):
        _inputs = self._param_inputs.copy()
        _type = _inputs.pop("_type")
        _registry = _inputs.pop("_registry")
        _name = self.params_label.text()

        if _registry is self.exclusion_registry and _name == "New Exclusion":
            self.mb.add_exclusion(_type, **_inputs)
        elif _registry is self.exclusion_registry:
            # modifying existing exclusion
            self.mb.remove_exclusion(_name)
            self.mb.add_exclusion(_type, **_inputs)
        elif _name == "New Layer":
            self.mb.add_layer(_type, **_inputs)
        else:
            self.mb.remove_layer(_name)
            self.mb.add_layer(_type, **_inputs)

        self._hide_and_clear_params_widget()
        self.configChanged.emit()

    def _generate_btn_widget(self, txt: str):
        btn = StyleButton(txt, parent=self)
        btn.setFixedHeight(32)
        font = btn.font()
        font.setPointSize(16)
        btn.setFont(font)
        btn.setEnabled(True)

        return btn

    @staticmethod
    def _generate_list_name(name, _type):
        return f"{name:<17} <type = {_type}>"

    @staticmethod
    def _get_layer_name_from_list_name(list_name):
        match = re.compile(
            r"(?P<name>\S+)\s+(<type = )(?P<type>\S+)(>)"
        ).fullmatch(list_name)
        return None if match is None else match.group("name")

    def _initialize_motion_builder(self):
        if (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mb, MotionBuilder)
            or not isinstance(self.mg.mb, MotionBuilder)
        ):
            pass
        elif self.mb is self.mg.mb:
            config = _deepcopy_dict(self.mb.config)
            self._spawn_motion_builder(config)
            return

        config = {"space": {}}
        for ii, aname in enumerate(self.axis_names):
            axis = self.mg.drive.axes[ii]

            if axis.units.physical_type == u.get_physical_type("length"):
                _range = [-55.0, 55.0]
                num = int(np.ceil((_range[1] - _range[0]) / .25))

                _convert = (1 * u.cm).to(axis.units)  # type: u.Quantity
                _convert = _convert.value
                _range = [float(r * _convert) for r in _range]
            elif axis.units.physical_type == u.get_physical_type("angle"):
                _x = 3 * 360.0
                delta = 5.0
                if axis.units == u.rad:
                    _x = _x * (2.0 * np.pi / 360.0)
                    delta = delta * (np.pi / 180.0)

                _range = [float(-_x), float(_x)]
                num = int(np.ceil(2.0 * _x / delta))
            else:  # this should not happen
                _range = [-1.0, 1.0]
                num = 11

            config["space"][ii] = {
                "label": aname,
                "range": _range,
                "num": num,
            }

        self._spawn_motion_builder(config)

    def _spawn_motion_builder(self, config):
        self.logger.info("Rebuilding motion builder...")
        space = list(config["space"].values())

        exclusions = config.get("exclusion", None)
        if exclusions is not None:
            exclusions = list(exclusions.values())

        layers = config.get("layer", None)
        if layers is not None:
            layers = list(layers.values())

        self.logger.info(f"space looks like : {space}")
        self.logger.info(f"exclusion look like : {exclusions}")
        self.logger.info(f"layer looks like : {layers}")

        self._mb = MotionBuilder(space=space, exclusions=exclusions, layers=layers)
        self.configChanged.emit()
        return self._mb

    def _validate_mb(self):
        if not isinstance(self.mb, MotionBuilder):
            self.done_btn.setEnabled(False)
            return
        elif len(self.mb.layers) == 0:
            self.done_btn.setEnabled(False)
            return

        self.done_btn.setEnabled(True)

    def return_and_close(self):
        config = self.mb.config

        self.logger.info(
            f"New MotionBuilder configuration is being returned, {config}."
        )
        self.returnConfig.emit(config)
        self.close()


class AxisControlWidget(QWidget):
    axisLinked = Signal()
    axisUnlinked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._logger = _logger

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
        self.jog_delta_label = _txt

        # Define ADVANCED WIDGETS

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self):
        self.jog_forward_btn.clicked.connect(self._jog_forward)
        self.jog_backward_btn.clicked.connect(self._jog_backward)
        self.zero_btn.clicked.connect(self._zero_axis)

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
        val = position.value[self.axis_index][0]
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
        # pos = self.axis.motor.status["position"]
        pos = self.position
        self.position_label.setText(f"{pos.value:.2f} {pos.unit}")

        if self.target_position_label.text() == "":
            self.target_position_label.setText(f"{pos.value:.2f}")

        limits = self.axis.motor.status["limits"]
        self.limit_fwd_btn.setChecked(limits["CW"])
        self.limit_bwd_btn.setChecked(limits["CCW"])

    def _zero_axis(self):
        self.axis.send_command("zero")

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

        self._logger = _logger

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
        self.mg.drive.send_command("zero")

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

        self.setEnabled(True)

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


class RunWidget(QWidget):
    def __init__(self, parent: "ConfigureGUI"):
        super().__init__(parent=parent)

        self._logger = _logger

        # Define BUTTONS

        _btn = StyleButton("DONE")
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        _btn.setFont(font)
        self.done_btn = _btn

        _btn = StyleButton("Discard && Quit")
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        font.setBold(True)
        _btn.setFont(font)
        _btn.update_style_sheet({"background-color": "rgb(255, 110, 110)"})
        self.quit_btn = _btn

        _btn = StyleButton("IMPORT")
        _btn.setFixedHeight(28)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        self.import_btn = _btn

        _btn = StyleButton("EXPORT")
        _btn.setFixedHeight(28)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        self.export_btn = _btn

        _btn = StyleButton("ADD")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        _btn.setEnabled(True)
        self.add_mg_btn = _btn

        _btn = StyleButton("REMOVE")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.remove_mg_btn = _btn

        _btn = StyleButton("Edit / Control")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.modify_mg_btn = _btn

        # Define TEXT WIDGETS

        self.config_widget = QTextEdit()
        self.mg_list_widget = QListWidget()

        _txt_widget = QLineEdit()
        font = _txt_widget.font()
        font.setPointSize(16)
        _txt_widget.setFont(font)
        self.run_name_widget = _txt_widget

        self.setLayout(self._define_layout())

        self._connect_signals()

    def _define_layout(self):

        # Create layout for banner (top header)
        banner_layout = self._define_banner_layout()

        # Create layout for toml window
        toml_widget = QWidget()
        toml_widget.setLayout(self._define_toml_layout())
        toml_widget.setMinimumWidth(400)
        toml_widget.setMinimumWidth(500)
        toml_widget.sizeHint().setWidth(450)

        # Create layout for controls
        control_widget = QWidget()
        control_widget.setLayout(self._define_control_layout())

        # Construct layout below top banner
        layout = QHBoxLayout()
        layout.addWidget(toml_widget)
        layout.addWidget(VLinePlain(parent=self))
        layout.addWidget(control_widget)

        # Populate the main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(banner_layout)
        main_layout.addLayout(layout)

        return main_layout

    def _define_toml_layout(self):
        layout = QGridLayout()
        label = QLabel("Run Configuration")
        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom
        )
        font = label.font()
        font.setPointSize(16)
        label.setFont(font)

        self.config_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        self.config_widget.setReadOnly(True)
        self.config_widget.font().setPointSize(14)
        self.config_widget.font().setFamily("Courier New")

        layout.addWidget(label, 0, 0, 1, 2)
        layout.addWidget(self.config_widget, 1, 0, 1, 2)
        layout.addWidget(self.import_btn, 2, 0, 1, 1)
        layout.addWidget(self.export_btn, 2, 1, 1, 1)

        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()

        layout.addWidget(self.quit_btn)
        layout.addStretch()
        layout.addWidget(self.done_btn)

        return layout

    def _define_control_layout(self):
        layout = QVBoxLayout()

        run_label = QLabel("Run Name:  ")
        run_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt. AlignmentFlag.AlignLeft
        )
        run_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = run_label.font()
        font.setPointSize(16)
        run_label.setFont(font)

        mg_label = QLabel("Defined Motion Groups")
        mg_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter
        )
        font = mg_label.font()
        font.setPointSize(16)
        mg_label.setFont(font)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(run_label)
        sub_layout.addWidget(self.run_name_widget)
        layout.addSpacing(18)
        layout.addLayout(sub_layout)
        layout.addSpacing(18)
        layout.addWidget(mg_label)
        layout.addWidget(self.mg_list_widget)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.add_mg_btn)
        sub_layout.addWidget(self.remove_mg_btn)
        layout.addLayout(sub_layout)

        layout.addWidget(self.modify_mg_btn)

        return layout

    def _connect_signals(self):
        self.mg_list_widget.itemClicked.connect(self.enable_mg_buttons)

    def enable_mg_buttons(self):
        self.add_mg_btn.setEnabled(True)
        self.remove_mg_btn.setEnabled(True)
        self.modify_mg_btn.setEnabled(True)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def rm(self) -> Union[RunManager, None]:
        parent = self.parent()  # type: "ConfigureGUI"
        try:
            return parent.rm
        except AttributeError:
            return None

    def closeEvent(self, event):
        self.logger.info("Closing RunWidget")
        event.accept()


class MGWidget(QWidget):
    closing = Signal()
    configChanged = Signal()
    returnConfig = Signal(int, object)

    mg_loop = asyncio.new_event_loop()

    def __init__(
        self, starting_mg: MotionGroup = None, parent: "ConfigureGUI" = None
    ):
        super().__init__(parent=parent)

        self._logger = _logger

        self._mg = None
        self._mg_index = None

        self._mg_config = None
        if isinstance(starting_mg, MotionGroup):
            self._mg_config = _deepcopy_dict(starting_mg.config)

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

        _btn = StyleButton("Configure DRIVE")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        self.drive_btn = _btn

        _btn = StyleButton("Motion Builder")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.mb_btn = _btn

        _btn = StyleButton("Set Transformer")
        _btn.setFixedHeight(32)
        font = _btn.font()
        font.setPointSize(16)
        _btn.setFont(font)
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

        layout = QVBoxLayout()
        layout.addSpacing(18)
        layout.addLayout(sub_layout)
        layout.addSpacing(18)
        layout.addWidget(self.drive_btn)
        layout.addWidget(self.mb_btn)
        layout.addWidget(self.transform_btn)
        layout.addStretch()

        return layout

    def _define_mspace_display_layout(self):
        ...

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
        self.logger.info("Replacing the motion group's drive.")
        self.mg.replace_drive(config)

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

        self.mg.drive.run()
        self._refresh_drive_control()
        self.configChanged.emit()

    def _refresh_drive_control(self):
        self.logger.info("Refreshing drive control widget.")
        if self.mg is None or self.mg.drive is None:
            self.drive_control_widget.unlink_motion_group()
            return

        self.drive_control_widget.link_motion_group(self.mg)

    def _update_toml_widget(self):
        self.toml_widget.setText(self.mg_config.as_toml_string)

    def _update_mg_name_widget(self):
        self.mg_name_widget.setText(self.mg_config["name"])

    def _rename_motion_group(self):
        self.mg.config["name"] = self.mg_name_widget.text()
        self.configChanged.emit()

    def _spawn_motion_group(self):
        self.logger.info("Spawning Motion Group")

        if isinstance(self.mg, MotionGroup):
            self.mg.terminate(delay_loop_stop=True)
            self._set_mg(None)

        try:
            mg = MotionGroup(
                config=self.mg_config,
                logger=self.logger,
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

    def return_and_close(self):
        config = _deepcopy_dict(self.mg.config)
        index = -1 if self._mg_index is None else self._mg_index

        self.logger.info(
            f"New MotionGroup configuration is being returned, {config}."
        )
        self.returnConfig.emit(index, config)
        self.close()

    def closeEvent(self, event):
        self.logger.info("Closing MGWidget")
        try:
            self.configChanged.disconnect()
        except RuntimeError:
            pass

        if self._overlay_widget is not None:
            self._overlay_widget.close()

        if isinstance(self.mg, MotionGroup):
            self.mg.terminate(delay_loop_stop=True)

        self.mg_loop.call_soon_threadsafe(self.mg_loop.stop)
        self.closing.emit()
        event.accept()


class ConfigureGUI(QMainWindow):
    _OPENED_FILE = None  # type: Union[Path, None]
    configChanged = Signal()

    def __init__(self):
        super().__init__()

        self._rm = None  # type: RunManager
        self._mg_being_modified = None  # type: MotionGroup

        # setup logger
        logging.config.dictConfig(self._logging_config_dict)
        self._logger = _logger
        self._rm_logger = logging.getLogger("RM")

        self._define_main_window()

        # define "important" qt widgets
        self._log_widget = QLogger(self._logger, parent=self)
        self._run_widget = RunWidget(self)
        self._mg_widget = None  # type: MGWidget

        self._stacked_widget = QStackedWidget(parent=self)
        self._stacked_widget.addWidget(self._run_widget)

        layout = self._define_layout()

        widget = QWidget(parent=self)
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self._rm_logger.addHandler(self._log_widget.handler)

        self._connect_signals()

        self.replace_rm({"name": "A New Run"})

    def _connect_signals(self):
        # Note: _mg_widget signals are connected in _spawn_mg_widget()
        #
        self._run_widget.import_btn.clicked.connect(self.toml_import)
        # self._run_widget.export_btn.clicked.connect(self.toml_export)
        self._run_widget.done_btn.clicked.connect(self.save_and_close)
        self._run_widget.quit_btn.clicked.connect(self.close)

        self._run_widget.add_mg_btn.clicked.connect(self._motion_group_configure_new)
        self._run_widget.remove_mg_btn.clicked.connect(self._motion_group_remove_from_rm)
        self._run_widget.modify_mg_btn.clicked.connect(
            self._motion_group_modify_existing
        )

        self._run_widget.run_name_widget.editingFinished.connect(self.change_run_name)

        self.configChanged.connect(self.update_display_config_text)
        self.configChanged.connect(self.update_display_rm_name)
        self.configChanged.connect(self.update_display_mg_list)

    def _define_main_window(self):
        self.setWindowTitle("Run Configuration")
        self.resize(1760, 990)
        self.setMinimumHeight(600)

    def _define_layout(self):

        self._log_widget.setMinimumWidth(400)
        self._log_widget.setMaximumWidth(500)
        self._log_widget.sizeHint().setWidth(450)
        self._log_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Ignored)

        layout = QHBoxLayout()
        layout.addWidget(self._stacked_widget)
        layout.addWidget(VLinePlain(parent=self))
        layout.addWidget(self._log_widget)

        return layout

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def rm(self) -> Union[RunManager, None]:
        return self._rm

    @rm.setter
    def rm(self, new_rm):
        if not isinstance(new_rm, RunManager):
            return
        elif isinstance(self._rm, RunManager):
            self._rm.terminate()

        self._rm = new_rm

    @property
    def _logging_config_dict(self):
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "class": "logging.Formatter",
                    "format": "%(asctime)s - [%(levelname)s] { %(name)s }  %(message)s",
                    "datefmt": "%H:%M:%S",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
                "stderr": {
                    "class": "logging.StreamHandler",
                    "level": "ERROR",
                    "formatter": "default",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "": {  # root logger
                    "level": "WARNING",
                    "handlers": ["stderr", "stdout"],
                    "propagate": True,
                },
                "GUI": {
                    "level": "DEBUG",
                    "handlers": [],
                    "propagate": True,
                },
                "RM": {
                    "level": "DEBUG",
                    "handlers": [],
                    "propagate": True,
                },
            },
        }

    def replace_rm(self, config):
        if isinstance(self.rm, RunManager):
            self.rm.terminate()

        self.logger.info(f"Replacing the run manager with new config: {config}.")
        _rm = RunManager(config=config, auto_run=True, build_mode=True)

        _remove = []
        for key, mg in _rm.mgs.items():
            if mg.drive.naxes != 2:
                self.logger.warning(
                    f"The Configuration GUI currently only supports motion"
                    f" groups with a dimensionality of 2, got {mg.drive.naxes}"
                    f" for motion group '{mg.name}'.  Removing motion group."
                )
                _remove.append(key)

        for key in _remove:
            _rm.remove_motion_group(key)

        self.rm = _rm
        self.configChanged.emit()

    def save_and_close(self):
        # save the toml configuration
        # TODO: write code to save current toml configuration to a tmp file

        self.close()

    def toml_export(self):
        ...

    def toml_import(self):
        path = QDir.currentPath() if self._OPENED_FILE is None \
            else f"{self._OPENED_FILE.parent}"

        file_name, _filter = QFileDialog.getOpenFileName(
            self,
            "Open file",
            path,
            "TOML file (*.toml)",
        )
        file_name = Path(file_name)

        if not file_name.is_file():
            # dialog was canceled
            return

        self.logger.info(f"Opening and reading file: {file_name} ...")

        with open(file_name, "rb") as f:
            run_config = toml.load(f)

        self.replace_rm(run_config)
        self._OPENED_FILE = file_name
        self.logger.info(f"... Success!")

    def update_display_config_text(self):
        self.logger.info(f"Updating the run config toml: {self.rm.config.as_toml_string}")
        self._run_widget.config_widget.setText(self.rm.config.as_toml_string)

    def update_display_rm_name(self):
        rm_name = self.rm.config["name"]
        self._run_widget.run_name_widget.setText(rm_name)

    def update_display_mg_list(self):
        self._run_widget.mg_list_widget.clear()
        self._run_widget.remove_mg_btn.setEnabled(False)
        self._run_widget.modify_mg_btn.setEnabled(False)

        if self.rm.mgs is None or not self.rm.mgs:
            return

        mg_labels = []
        for key, val in self.rm.mgs.items():
            label = self._generate_mg_list_name(key, val.config["name"])
            mg_labels.append(label)

        self._run_widget.mg_list_widget.addItems(mg_labels)

    def change_run_name(self):
        name = self._run_widget.run_name_widget.text()

        if self.rm is None:
            self.replace_rm({"name": name})
        else:
            self.rm.config.update_run_name(name)
            self.configChanged.emit()

    def _motion_group_configure_new(self):
        self._spawn_mg_widget()
        self._switch_stack()

    def _motion_group_modify_existing(self):
        item = self._run_widget.mg_list_widget.currentItem()
        key, mg_name = self._get_mg_name_from_list_name(item.text())
        mg = self.rm.mgs[key]
        mg.terminate(delay_loop_stop=True)
        self._mg_being_modified = mg
        self._spawn_mg_widget(mg)
        self._mg_widget.mg_index = key
        self._switch_stack()

    def _motion_group_remove_from_rm(self):
        item = self._run_widget.mg_list_widget.currentItem()
        identifier, mg_name = self._get_mg_name_from_list_name(item.text())
        self.rm.remove_motion_group(identifier=identifier)
        self.configChanged.emit()

    def _restart_motion_group(self):
        if self._mg_being_modified is not None:
            self.logger.info(f"Restarting motion group '{self._mg_being_modified.name}'.")
            self._mg_being_modified.run()
            self._mg_being_modified = None

    def _spawn_mg_widget(self, mg: MotionGroup = None):
        self._mg_widget = MGWidget(mg, parent=self)
        self._mg_widget.closing.connect(self._switch_stack)
        self._mg_widget.returnConfig.connect(self.add_mg_to_rm)
        self._mg_widget.discard_btn.clicked.connect(self._restart_motion_group)

        return self._mg_widget

    @Slot(int, object)
    def add_mg_to_rm(self, index: int, mg_config: Dict[str, Any]):
        index = None if index == -1 else index

        self.logger.info(
            f"Adding MotionGroup to the run: index = '{index}', config = {mg_config}."
        )
        self.rm.add_motion_group(config=mg_config, identifier=index)
        self._mg_being_modified = None
        self.configChanged.emit()

    @staticmethod
    def _generate_mg_list_name(index, mg_name):
        return f"[{index:2d}]   {mg_name}"

    @staticmethod
    def _get_mg_name_from_list_name(list_name):
        match = re.compile(
            r"\[\s*(?P<index>[0-9]+)\]\s+(?P<name>.+)"
        ).fullmatch(list_name)
        return (
            None
            if match is None
            else (int(match.group("index")), match.group("name"))
        )

    def _switch_stack(self):
        _w = self._stacked_widget.currentWidget()
        if isinstance(_w, RunWidget):
            self._stacked_widget.addWidget(self._mg_widget)
            self._stacked_widget.setCurrentWidget(self._mg_widget)
        else:
            # the stack widget is the MGWidget instance
            self._stacked_widget.removeWidget(_w)
            self._stacked_widget.setCurrentIndex(0)
            _w.close()
            _w.deleteLater()
            self._mg_widget = None

    def closeEvent(self, event: "QCloseEvent") -> None:
        self.logger.info("Closing ConfigureGUI")

        self._run_widget.close()
        if isinstance(self._mg_widget, MGWidget):
            self._mg_widget.close()

        if self.rm is not None:
            self.rm.terminate()

        event.accept()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
