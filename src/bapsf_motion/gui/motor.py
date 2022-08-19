from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QSizePolicy,
    QSlider,
    QTextEdit,
    QFrame,
    QLineEdit,
    QPushButton,
)
from typing import Any, Dict

from __feature__ import snake_case  # noqa


class StopButton(QPushButton):
    default_style = """
    background-color: rgb(255,90,90);
    border-radius: 6px;
    border: 2px solid black;
    """
    pressed_style = """
    background-color: rgb(90,255,90)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.set_style_sheet(self.default_style)
        # self.set_checkable(True)

        self.set_style_sheet("""
        StopButton {
          background-color: rgb(255,130,130);
          border-radius: 6px;
          border: 1px solid black;
        }
        
        StopButton:hover {
          border: 3px solid black;
          background-color: rgb(255,70,70);
        }
        """)

        # self.pressed.connect(self.toggle_style)
        # self.released.connect(self.toggle_style)

    def toggle_style(self):
        style = self.pressed_style if self.is_checked() else self.default_style
        self.set_style_sheet(style)


class MotorGUI(QMainWindow):
    _log_verbosity = 1
    _log_widgets = {
        "verbosity_label": None,
        "log_box": None,
    }  # type: Dict[str, Any]
    _control_widgets = {
        "ip": None,
        "stop": None,
    }  # type: Dict[str, Any]

    def __init__(self):
        super().__init__()

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
        log_widget.set_minimum_width(300)
        log_widget.set_maximum_width(700)
        log_widget.size_hint().set_width(500)
        log_widget.set_size_policy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.add_widget(log_widget, stretch=500)

        widget = QWidget()
        widget.set_layout(layout)
        self.set_central_widget(widget)

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
        self._log_widgets["verbosity_label"] = label

        row2_layout.add_widget(slider)
        row2_layout.add_widget(label)
        layout.add_layout(row2_layout)

        # third row: text box
        txt_box = QTextEdit()
        layout.add_widget(txt_box)

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
        self._control_widgets["stop"] = stop_btn
        layout.add_widget(stop_btn)

        # row 3: Initial Controls/Indicators
        row2_layout = QHBoxLayout()

        label = QLabel("IP Address:")
        font = label.font()
        font.set_point_size(12)
        label.set_font(font)
        row2_layout.add_widget(label, alignment=Qt.AlignTop)


        ip_widget = QLineEdit()
        ip_widget.set_input_mask("000.000.000.000")
        ip_widget.set_maximum_width(100)
        ip_widget.set_size_policy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row2_layout.add_spacing(4)
        row2_layout.add_widget(ip_widget, alignment=Qt.AlignLeft)

        row2_layout.add_stretch()

        layout.add_layout(row2_layout)

        # full bottom with blank space
        layout.add_stretch()
        # layout.add_spacing(self.height())

        return layout

    @property
    def log_verbosity(self):
        return self._log_verbosity

    @log_verbosity.setter
    def log_verbosity(self, value):
        self._log_verbosity = value

    def update_log_verbosity(self, value):
        self.log_verbosity = value
        self._log_widgets["verbosity_label"].set_text(f"{value}")

    def stop_moving(self):
        # send command to stop moving
        ...




if __name__ == "__main__":
    app = QApplication([])

    window = MotorGUI()
    window.show()

    app.exec()
