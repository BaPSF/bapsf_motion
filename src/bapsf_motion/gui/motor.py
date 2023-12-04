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

from typing import Any, Dict

from bapsf_motion.actors import Motor
from bapsf_motion.gui.widgets import QLogHandler, LED, StopButton, IPv4Validator


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

        self.setWindowTitle("Motor GUI")
        self.resize(1600, 900)
        self.setMinimumHeight(600)

        layout = QHBoxLayout()

        # control_widget = QLabel()
        # control_widget.set_frame_style(QFrame.StyledPanel | QFrame.Plain)
        # control_widget.set_minimum_width(800)
        control_widget = QWidget()
        control_widget.setMinimumWidth(800)
        control_widget.setLayout(self.control_layout)
        layout.addWidget(control_widget, stretch=1100)

        vbar = QLabel()
        vbar.setFrameStyle(QFrame.VLine | QFrame.Plain)
        vbar.setLineWidth(2)
        layout.addWidget(vbar)

        log_widget = QWidget()
        log_widget.setLayout(self.log_layout)
        log_widget.setMinimumWidth(400)
        log_widget.setMaximumWidth(800)
        log_widget.sizeHint().setWidth(600)
        log_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.addWidget(log_widget, stretch=600)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # this needs to be done after the GUI is set up
        self._configure_logger()

    @property
    def log_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("LOG")
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # second row: verbosity setting
        row2_layout = QHBoxLayout()

        label = QLabel("Verbosity")
        label.setMinimumWidth(75)
        font = label.font()
        font.setPointSize(12)
        label.setFont(font)
        row2_layout.addWidget(
            label,
            alignment=Qt.AlignCenter | Qt.AlignLeft,
        )

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(4)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setTickPosition(slider.TickPosition.TicksBelow)
        slider.setFixedHeight(16)
        slider.setMinimumWidth(100)
        slider.valueChanged.connect(self.update_log_verbosity)

        label = QLabel(f"{self.log_verbosity}")
        label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        label.setMinimumWidth(24)
        font = label.font()
        font.setPointSize(12)
        label.setFont(font)
        self._log["verbosity_label"] = label

        row2_layout.addWidget(slider)
        row2_layout.addWidget(label)
        layout.addLayout(row2_layout)

        # third row: text box
        log_box = QTextEdit()
        font = log_box.font()
        font.setPointSize(10)
        font.setFamily("Courier New")
        log_box.setFont(font)
        # log_box = QPlainTextEdit()
        log_box.setReadOnly(True)
        self._log["log_box"] = log_box
        layout.addWidget(log_box)

        return layout

    @property
    def control_layout(self):
        layout = QVBoxLayout()

        # row 1: Title
        label = QLabel("Motor Class Debugger GUI")
        font = label.font()
        font.setPointSize(16)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # row 2: STOP Button
        # stop_btn = QPushButton("STOP")
        stop_btn = StopButton("STOP")
        stop_btn.setFixedHeight(72)
        font = stop_btn.font()
        font.setPointSize(36)
        font.setBold(True)
        stop_btn.setFont(font)
        # stop_btn.set_style_sheet("""
        # background-color: rgb(255,90,90);
        # border-radius: 6px;
        # border: 2px solid black;
        # box-shadow: -3px 3px orange, -2px 2px orange, -1px 1px orange;
        # }
        # """)
        # stop_btn.clicked.connect(self.stop_moving)
        self._controls["stop"] = stop_btn
        layout.addWidget(stop_btn)

        # row 3: Initial Controls/Indicators
        row2_layout = QHBoxLayout()

        label = QLabel("IP Address:")
        font = label.font()
        font.setPointSize(14)
        label.setFont(font)
        row2_layout.addWidget(label, alignment=Qt.AlignTop)

        ip_widget = QLineEdit()
        font = ip_widget.font()
        font.setPointSize(14)
        font.setFamily("Courier New")
        ip_widget.setFont(font)
        ip_widget.setInputMask("009.009.009.009;_")
        ip_widget.setValidator(IPv4Validator(logger=self.logger))
        ip_widget.setMaximumWidth(200)
        ip_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        ip_widget.textEdited.connect(self.deactivate_motor)
        ip_widget.editingFinished.connect(self.process_new_ip)
        # ip_widget.inputRejected.connect(self.process_new_ip)
        self._controls["ip"] = ip_widget
        row2_layout.addSpacing(4)
        row2_layout.addWidget(ip_widget, alignment=Qt.AlignLeft)

        led = LED()
        led.setFixedHeight(18)
        led.setChecked(False)
        self._indicators["valid_ip"] = led
        row2_layout.addSpacing(4)
        row2_layout.addWidget(led)

        row2_layout.addLayout(self.indicator_widget)
        row2_layout.addStretch()

        layout.addLayout(row2_layout)

        # fill bottom with blank space
        layout.addStretch()

        return layout

    @property
    def indicator_widget(self):
        layout = QGridLayout()

        font = QFont()
        font.setPointSize(16)

        # add Connected indicator
        label = QLabel("Connected")
        label.setFont(font)
        led = LED()
        led.setFixedHeight(18)
        led.setChecked(False)
        self._indicators["connected"] = led
        layout.addWidget(label, 0, 0)
        layout.addWidget(led, 0, 1)

        # add Enabled indicator
        label = QLabel("Enabled")
        label.setFont(font)
        led = LED()
        led.setFixedHeight(18)
        led.setChecked(False)
        self._indicators["enabled"] = led
        layout.addWidget(label, 0, 2)
        layout.addWidget(led, 0, 3)

        # widget = QWidget()
        # widget.setLayout(layout)

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
        self._log["verbosity_label"].setText(f"{value}")

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
