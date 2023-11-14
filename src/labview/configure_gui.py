import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QGridLayout,
    QWidget,
    QTextEdit,
    QSizePolicy,
)
from typing import Any, Dict

from bapsf_motion.gui.widgets import QLogHandler


class ConfigureGUI(QMainWindow):
    logger = None
    _log = {
        "verbosity": 1,
        "verbosity_label": None,
        "log_box": None,
    }  # type: Dict[str, Any]

    def __init__(self):
        super().__init__()

        self.define_main_window()

        layout = QHBoxLayout()

        layout.addWidget(self.dummy_widget())
        layout.addWidget(self.logging_widget())

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # this needs to be done after the GUI is set up
        # self._configure_logger()

    def define_main_window(self):
        self.setWindowTitle("Run Configuration")
        self.resize(1600, 900)
        self.setMinimumHeight(600)

    def dummy_layout(self):
        layout = QGridLayout()
        layout.addWidget(QLabel("Dummy Widget"), 0, 0)

        return layout

    def dummy_widget(self):
        widget = QWidget()
        widget.setLayout(self.dummy_layout())

        return widget

    def logging_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("LOG")
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # second row: verbosity setting
        row2_layout = QGridLayout()

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(5)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.setTickPosition(slider.TickPosition.TicksBelow)
        slider.setFixedHeight(16)
        slider.setMinimumWidth(100)
        # slider.valueChanged.connect(self.update_log_verbosity)

        label_widgets = []
        for label in ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR"]:
            lw = QLabel(label)
            lw.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            lw.setMinimumWidth(24)

            font = lw.font()
            font.setPointSize(12)
            lw.setFont(font)

            label_widgets.append(lw)

        row2_layout.addWidget(slider, 0, 1, 1, 8)
        for ii, lw in enumerate(label_widgets):
            row2_layout.addWidget(lw, 1, 2*ii, 1, 2)

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

    def logging_widget(self):
        widget = QWidget()
        widget.setLayout(self.logging_layout())
        widget.setMinimumWidth(400)
        widget.setMaximumWidth(600)
        widget.sizeHint().setWidth(500)
        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        return widget

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


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
