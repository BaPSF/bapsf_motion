import asyncio
import logging
import logging.config

from pathlib import Path
from PySide6.QtCore import Qt, QDir, Signal
from PySide6.QtGui import QCloseEvent, QColor, QPainter
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
)
from typing import Any, Dict, List, Union

from bapsf_motion.actors import RunManager, MotionGroup, Drive, Axis, Motor
from bapsf_motion.gui.widgets import QLogger, StyleButton, LED
from bapsf_motion.utils import toml, ipv4_pattern

_logger = logging.getLogger(":: GUI ::")


class _OverlayWidget(QWidget):
    closing = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

        # make the window frameless
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("border: 2px solid black")

        self.background_fill_color = QColor(30, 30, 30, 120)
        self.background_pen_color = QColor(30, 30, 30, 120)

        self.overlay_fill_color = QColor(50, 50, 50)
        self.overlay_pen_color = QColor(90, 90, 90)

        self._margins = [0.02, 0.04]
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
        _btn = LED()
        _btn.set_fixed_height(24)
        self.online_led = _btn

        # Define TEXT WIDGETS
        _widget = QLabel(name, parent=self)
        font = _widget.font()
        font.setPointSize(32)
        _widget.setFont(font)
        _widget.setFixedWidth(30)
        self.ax_name_widget = _widget

        _widget = QLineEdit()
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setMinimumWidth(220)
        self.ip_widget = _widget

        _widget = QLineEdit()
        font = _widget.font()
        font.setPointSize(16)
        _widget.setFont(font)
        _widget.setFixedWidth(120)
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

    def set_ip_handler(self, handler: callable):
        self._ip_handlers.append(handler)

    def _validate_ip(self, ip):
        if ipv4_pattern.fullmatch(ip) is None:
            self.logger.error(
                f"Supplied IP address ({ip}) is not a valid IPv4."
            )
            return

        for handler in self._ip_handlers:
            ip = handler(ip)

            if ip is None or ip == "":
                return

        return ip

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

    def closeEvent(self, event):
        self.logger.info("Closing AxisConfigWidget")

        if isinstance(self.axis, Axis):
            self.axis.terminate(delay_loop_stop=True)

        self.axis_loop.call_soon_threadsafe(self.axis_loop.stop)

        event.accept()


class DriveConfigOverlay(_OverlayWidget):

    def __init__(self, parent: "MGWidget" = None):
        super().__init__(parent)

        self._logger = _logger

        # Define BUTTONS

        _btn = StyleButton("Save to MG")
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = StyleButton("Discard && Return")
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
        self.axis_widgets = {}

        self.setLayout(self._define_layout())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connect_signals()

    @property
    def logger(self):
        return self._logger

    def _define_layout(self):
        _hline = QFrame()
        _hline.setFrameShape(QFrame.Shape.HLine)
        _hline.setFrameShadow(QFrame.Shadow.Plain)
        _hline.setLineWidth(3)
        _hline.setMidLineWidth(3)
        _hline.setStyleSheet("border-color: rgb(95, 95, 95)")
        hline = _hline

        layout = QVBoxLayout()
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(hline)
        layout.addLayout(self._define_second_row_layout())
        layout.addSpacing(24)
        layout.addWidget(self._init_axis_widget("X"))
        layout.addWidget(self._init_axis_widget("Y"))
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

    def _init_axis_widget(self, name):
        _frame = QFrame()
        _frame.setLayout(QVBoxLayout())

        _widget = AxisConfigWidget(name)
        # _widget.setStyleSheet(
        #     "border: 3px solid rgb(95, 95, 95);"
        #     "border-radius: 5px;"
        # )

        self.axis_widgets[name] = _widget

        _frame.layout().addWidget(_widget)
        _frame.setStyleSheet(
            "border: 3px solid rgb(95, 95, 95);"
            "border-radius: 5px;"
            "padding: 6px;"
        )

        return _frame

    def _connect_signals(self):
        self.done_btn.clicked.connect(self.close)
        self.discard_btn.clicked.connect(self.close)


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

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setStyleSheet("color: rgb(95, 95, 95)")
        vline.setLineWidth(10)

        # Construct layout below top banner
        layout = QHBoxLayout()
        layout.addWidget(toml_widget)
        layout.addWidget(vline)
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


class MGWidget(QWidget):
    configChanged = Signal()

    def __init__(self, parent: "ConfigureGUI"):
        super().__init__(parent=parent)

        self._logger = _logger

        self._mg = None
        self._mg_index = None

        # Define BUTTONS

        _btn = StyleButton("Add to Run")
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(48)
        font = _btn.font()
        font.setPointSize(24)
        _btn.setFont(font)
        _btn.setEnabled(False)
        self.done_btn = _btn

        _btn = StyleButton("Discard && Return to Run")
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
        self._overlay_widget = None  # type: Union[_OverlayWidget, None]
        self._overlay_shown = False

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _define_layout(self):

        _hline = QFrame()
        _hline.setFrameShape(QFrame.Shape.HLine)
        _hline.setStyleSheet("color: rgb(95, 95, 95)")
        _hline.setLineWidth(10)
        hline1 = _hline

        _hline = QFrame()
        _hline.setFrameShape(QFrame.Shape.HLine)
        _hline.setStyleSheet("color: rgb(95, 95, 95)")
        _hline.setLineWidth(10)
        hline2 = _hline

        layout = QVBoxLayout()
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(hline1)
        layout.addLayout(self._define_mg_builder_layout(), 2)
        layout.addWidget(hline2)
        layout.addStretch(1)

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

    def _connect_signals(self):
        self.drive_btn.clicked.connect(self._popup_drive_configuration)

        self.mg_name_widget.editingFinished.connect(self._rename_motion_group)

        self.configChanged.connect(self._update_toml_widget)
        self.configChanged.connect(self._update_mg_name_widget)

    def _popup_drive_configuration(self):
        _overlay = DriveConfigOverlay(self)
        _overlay.move(0, 0)
        _overlay.resize(self.width(), self.height())
        _overlay.closing.connect(self._overlay_close)
        self._overlay_widget = _overlay
        self._overlay_widget.show()
        self._overlay_shown = True

    def _overlay_close(self):
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

    @mg.setter
    def mg(self, val: "MotionGroup"):
        if isinstance(val, MotionGroup):
            self._mg = val

            self.configChanged.emit()

    def _update_toml_widget(self):
        self.toml_widget.setText(self.mg.config.as_toml_string)

    def _update_mg_name_widget(self):
        self.mg_name_widget.setText(self.mg.config["name"])

    def _rename_motion_group(self):
        self.mg.config["name"] = self.mg_name_widget.text()
        self.configChanged.emit()

    def closeEvent(self, event):
        self.logger.info("Closing MGWidget")
        if self._overlay_widget is not None:
            self._overlay_widget.close()
        event.accept()


class ConfigureGUI(QMainWindow):
    _OPENED_FILE = None  # type: Union[Path, None]
    configChanged = Signal()

    def __init__(self):
        super().__init__()

        self._rm = None

        # setup logger
        logging.config.dictConfig(self._logging_config_dict)
        self._logger = _logger
        self._rm_logger = logging.getLogger("RM")

        self._define_main_window()

        # define "important" qt widgets
        self._log_widget = QLogger(self._logger)
        self._run_widget = RunWidget(self)
        self._mg_widget = MGWidget(self)
        self._stacked_widget = QStackedWidget()
        self._stacked_widget.addWidget(self._run_widget)
        self._stacked_widget.addWidget(self._mg_widget)
        self._stacked_widget.setCurrentWidget(self._mg_widget)

        layout = self._define_layout()

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self._rm_logger.addHandler(self._log_widget.handler)

        self._connect_signals()

        self.replace_rm({"name": "A New Run"})

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
                    "format": "%(asctime)s - [%(levelname)s] %(name)s  %(message)s",
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
                ":: GUI ::": {
                    "level": "DEBUG",
                    "handlers": ["stderr"],
                    "propagate": True,
                },
                "RM": {
                    "level": "DEBUG",
                    "handlers": ["stderr"],
                    "propagate": True,
                },
            },
        }

    def _define_main_window(self):
        self.setWindowTitle("Run Configuration")
        self.resize(1760, 990)
        self.setMinimumHeight(600)

    def _define_layout(self):
        layout = QHBoxLayout()

        # layout.addWidget(self.dummy_widget())
        # layout.addWidget(self._run_widget)
        layout.addWidget(self._stacked_widget)

        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setMidLineWidth(3)
        layout.addWidget(vline)

        self._log_widget.setMinimumWidth(400)
        self._log_widget.setMaximumWidth(500)
        self._log_widget.sizeHint().setWidth(450)
        self._log_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Ignored)
        layout.addWidget(self._log_widget)

        return layout

    def _connect_signals(self):
        self._run_widget.import_btn.clicked.connect(self.import_file)
        self._run_widget.done_btn.clicked.connect(self.save_and_close)
        self._run_widget.quit_btn.clicked.connect(self.close)
        self._run_widget.add_mg_btn.clicked.connect(self._switch_stack)

        self._run_widget.run_name_widget.editingFinished.connect(self.change_run_name)

        self._mg_widget.discard_btn.clicked.connect(self._switch_stack)
        self._mg_widget.done_btn.clicked.connect(self._switch_stack)

        self.configChanged.connect(self.update_display_config_text)
        self.configChanged.connect(self.update_display_rm_name)
        self.configChanged.connect(self.update_display_mg_list)

    def closeEvent(self, event: "QCloseEvent") -> None:
        self.logger.info("Closing ConfigureGUI")
        self._run_widget.close()
        self._mg_widget.close()

        if self.rm is not None:
            self.rm.terminate()

        event.accept()

    def replace_rm(self, config):
        if isinstance(self.rm, RunManager):
            self.rm.terminate()

        _rm = RunManager(config=config, auto_run=True, build_mode=True)
        self.rm = _rm
        self.configChanged.emit()

    def save_and_close(self):
        # save the toml configuration
        # TODO: write code to save current toml configuration to a tmp file

        self.close()

    def import_file(self):
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
        self._run_widget.config_widget.setText(self.rm.config.as_toml_string)

    def update_display_rm_name(self):
        rm_name = self.rm.config["name"]
        self._run_widget.run_name_widget.setText(rm_name)

    def update_display_mg_list(self):
        mg_labels = []

        if self.rm.config._mgs is None:
            return

        for key, val in self.rm.config._mgs.items():
            label = f"[{key}] {val.config['name']}"
            mg_labels.append(label)

        self._run_widget.mg_list_widget.clear()
        self._run_widget.mg_list_widget.addItems(mg_labels)

    def change_run_name(self):
        name = self._run_widget.run_name_widget.text()

        if self.rm is None:
            self.replace_rm({"name": name})
        else:
            self.rm.config.update_run_name(name)
            self.configChanged.emit()

    def _switch_stack(self):
        index = self._stacked_widget.currentIndex()
        switch_to = 0 if index == 1 else 1
        self._stacked_widget.setCurrentIndex(switch_to)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
