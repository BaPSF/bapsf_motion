import logging
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QSizePolicy,
    QSlider,
    QTextEdit,
    QFrame,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
)

from __feature__ import snake_case  # noqa

from typing import Any, Dict

from bapsf_motion.actors import Motor
from bapsf_motion.gui.widgets import LED, StopButton, QLogHandler, IPv4Validator


class MotorGUI(QMainWindow):
    motor = None
    logger = None
    _log = {
        "verbosity": 1,
        "verbosity_label": None,
        "log_box": None,
    }  # type: Dict[str, Any]
    _controls = {
        "ip": None,
        "stop": None,
    }  # type: Dict[str, Any]
    _indicators = {
        "valid_ip": None,
        "connected": False,
        "moving": False,
        "jogging": False,
        "alarm": False,
        "fault": False,
        "position": None,
    }  # type: Dict[str, Any]

    def __init__(self):
        super().__init__()

        logging.basicConfig(level=logging.NOTSET)
        self.logger = logging.getLogger("MotorGUI")

        self.set_window_title("Motor GUI")
        self.resize(1600, 900)
        self.set_minimum_height(600)

        layout = QHBoxLayout()

        # control_widget = QLabel()
        # control_widget.set_frame_style(QFrame.StyledPanel | QFrame.Plain)
        # control_widget.set_minimum_width(800)
        control_widget = QWidget()
        control_widget.set_minimum_width(800)
        control_widget.set_layout(self.control_layout)
        layout.add_widget(control_widget, stretch=1100)

        vbar = QLabel()
        vbar.set_frame_style(QFrame.VLine | QFrame.Plain)
        vbar.set_line_width(2)
        layout.add_widget(vbar)

        log_widget = QWidget()
        log_widget.set_layout(self.log_layout)
        log_widget.set_minimum_width(400)
        log_widget.set_maximum_width(800)
        log_widget.size_hint().set_width(600)
        log_widget.set_size_policy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.add_widget(log_widget, stretch=600)

        widget = QWidget()
        widget.set_layout(layout)
        self.set_central_widget(widget)

        # this needs to be done after the GUI is set up
        self._configure_logger()

    @property
    def log_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("LOG")
        font = label.font()
        font.set_point_size(14)
        font.set_bold(True)
        label.set_font(font)
        layout.add_widget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # second row: verbosity setting
        row2_layout = QHBoxLayout()

        label = QLabel("Verbosity")
        label.set_minimum_width(75)
        font = label.font()
        font.set_point_size(12)
        label.set_font(font)
        row2_layout.add_widget(
            label,
            alignment=Qt.AlignCenter | Qt.AlignLeft,
        )

        slider = QSlider(Qt.Horizontal)
        slider.set_minimum(1)
        slider.set_maximum(4)
        slider.set_tick_interval(1)
        slider.set_single_step(1)
        slider.set_tick_position(slider.TicksBelow)
        slider.set_fixed_height(16)
        slider.set_minimum_width(100)
        slider.valueChanged.connect(self.update_log_verbosity)

        label = QLabel(f"{self.log_verbosity}")
        label.set_alignment(Qt.AlignCenter | Qt.AlignVCenter)
        label.set_minimum_width(24)
        font = label.font()
        font.set_point_size(12)
        label.set_font(font)
        self._log["verbosity_label"] = label

        row2_layout.add_widget(slider)
        row2_layout.add_widget(label)
        layout.add_layout(row2_layout)

        # third row: text box
        log_box = QTextEdit()
        font = log_box.font()
        font.set_point_size(10)
        font.set_family("Courier New")
        log_box.set_font(font)
        # log_box = QPlainTextEdit()
        log_box.set_read_only(True)
        self._log["log_box"] = log_box
        layout.add_widget(log_box)

        return layout

    @property
    def control_layout(self):
        layout = QVBoxLayout()

        # row 1: Title
        label = QLabel("Motor Class Debugger GUI")
        font = label.font()
        font.set_point_size(16)
        font.set_bold(True)
        label.set_font(font)
        layout.add_widget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # row 2: STOP Button
        # stop_btn = QPushButton("STOP")
        stop_btn = StopButton("STOP")
        stop_btn.set_fixed_height(72)
        font = stop_btn.font()
        font.set_point_size(36)
        font.set_bold(True)
        stop_btn.set_font(font)
        # stop_btn.set_style_sheet("""
        # background-color: rgb(255,90,90);
        # border-radius: 6px;
        # border: 2px solid black;
        # box-shadow: -3px 3px orange, -2px 2px orange, -1px 1px orange;
        # }
        # """)
        # stop_btn.clicked.connect(self.stop_moving)
        self._controls["stop"] = stop_btn
        layout.add_widget(stop_btn)

        # row 3: Initial Controls/Indicators
        row2_layout = QHBoxLayout()

        label = QLabel("IP Address:")
        font = label.font()
        font.set_point_size(14)
        label.set_font(font)
        row2_layout.add_widget(label, alignment=Qt.AlignTop)

        ip_widget = QLineEdit()
        font = ip_widget.font()
        font.set_point_size(14)
        font.set_family("Courier New")
        ip_widget.set_font(font)
        ip_widget.set_input_mask("009.009.009.009;_")
        ip_widget.set_validator(IPv4Validator(logger=self.logger))
        ip_widget.set_maximum_width(200)
        ip_widget.set_size_policy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        ip_widget.textEdited.connect(self.deactivate_motor)
        ip_widget.editingFinished.connect(self.process_new_ip)
        # ip_widget.inputRejected.connect(self.process_new_ip)
        self._controls["ip"] = ip_widget
        row2_layout.add_spacing(4)
        row2_layout.add_widget(ip_widget, alignment=Qt.AlignLeft)

        led = LED()
        led.set_fixed_height(18)
        led.set_checked(False)
        self._indicators["valid_ip"] = led
        row2_layout.add_spacing(4)
        row2_layout.add_widget(led)

        row2_layout.add_layout(self.indicator_widget)
        row2_layout.add_stretch()

        layout.add_layout(row2_layout)

        # fill bottom with blank space
        layout.add_stretch()

        return layout

    @property
    def indicator_widget(self):
        layout = QGridLayout()

        font = QFont()
        font.set_point_size(16)

        # add Connected indicator
        label = QLabel("Connected")
        label.set_font(font)
        led = LED()
        led.set_fixed_height(18)
        led.set_checked(False)
        self._indicators["connected"] = led
        layout.add_widget(label, 0, 0)
        layout.add_widget(led, 0, 1)

        # add Enabled indicator
        label = QLabel("Enabled")
        label.set_font(font)
        led = LED()
        led.set_fixed_height(18)
        led.set_checked(False)
        self._indicators["enabled"] = led
        layout.add_widget(label, 0, 2)
        layout.add_widget(led, 0, 3)

        widget = QWidget()
        widget.set_layout()

        return layout

    @property
    def log_verbosity(self):
        return self._log["verbosity"]

    @log_verbosity.setter
    def log_verbosity(self, value):
        self._log["verbosity"] = value

    def _configure_logger(self):
        _format = logging.Formatter(
            "[{name}] - {levelname}: {message}", style="{"
        )
        _handler = QLogHandler(widget=self._log["log_box"])
        _handler.setFormatter(_format)

        self.logger.addHandler(_handler)

    def update_log_verbosity(self, value):
        self.log_verbosity = value
        self._log["verbosity_label"].set_text(f"{value}")

    def stop_moving(self):
        # send command to stop moving
        ...

    def process_new_ip(self):
        name = "WALL-E"
        ip = self._controls["ip"].text()
        self.logger.debug(f"New IP enter: '{ip}'")
        self.logger.debug(f"Establishing new motor {name}")

        try:
            self.motor = Motor(ip=ip, name=name, logger=self.logger)
            self._indicators["valid_ip"].set_checked(True)
        except Exception as err:
            self.logger.error(
                f"Motor {name} failed to connect. {type(err).__name__}: {err}"
            )
            self.motor = None

    def deactivate_motor(self, new_ip):
        if self.motor is None:
            return

        self._indicators["valid_ip"].set_checked(False)
        msg = f"New IP address being entered, '{new_ip}'"
        self.logger.debug(msg)

        self.motor.stop()
        self.motor = None


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = MotorGUI()
    window.show()

    app.exec()
