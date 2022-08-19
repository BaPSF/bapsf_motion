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
)
from typing import Any, Dict

from __feature__ import snake_case  # noqa


class MotorGUI(QMainWindow):
    _log_verbosity = 1
    _log_widgets = {
        "verbosity_label": None,
        "log_box": None,
    }  # type: Dict[str, Any]

    def __init__(self):
        super().__init__()

        self.set_window_title("Motor GUI")
        self.resize(1600, 900)
        self.set_minimum_height(600)

        layout = QHBoxLayout()

        control_widget = QLabel()
        control_widget.set_frame_style(QFrame.StyledPanel | QFrame.Plain)
        control_widget.set_minimum_width(800)
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
    def log_verbosity(self):
        return self._log_verbosity

    @log_verbosity.setter
    def log_verbosity(self, value):
        self._log_verbosity = value

    def update_log_verbosity(self, value):
        self.log_verbosity = value
        self._log_widgets["verbosity_label"].set_text(f"{value}")


if __name__ == "__main__":
    app = QApplication([])

    window = MotorGUI()
    window.show()

    app.exec()
