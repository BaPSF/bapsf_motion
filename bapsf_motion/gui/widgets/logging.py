"""
This module contains custom Qt widgets for displaying logs generated
by Python's `logging` package.
"""

__all__ = ["QLogHandler", "QLogger"]

import logging
import logging.config

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from typing import Union

# import of bapssf_qt must happen after the PySide6 imports
from bapsf_qt.widgets import QLogHandler, QLogger  # noqa


class DemoQLogger(QMainWindow):
    def __init__(self):
        super().__init__()

        logging.config.dictConfig(self._logging_config_dict)
        self._logger = logging.getLogger(":: GUI ::")

        self._define_main_window()

        self._msg_widget = QLineEdit()
        self._level_widget = QComboBox()

        layout = self._define_layout()

        self._msg_widget.returnPressed.connect(self.enter_log)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

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
            },
        }

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def _define_main_window(self):
        self.setWindowTitle("Log Widget Tester")
        self.resize(800, 900)
        self.setMinimumHeight(600)

    def _define_layout(self):
        layout = QVBoxLayout()

        # first row: Title
        label = QLabel("DEMO: QLogger")
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, alignment=Qt.AlignHCenter | Qt.AlignTop)

        layout.addSpacing(24)

        sublayout = QHBoxLayout()
        label = QLabel("Message:  ")
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sublayout.addWidget(label)

        self._msg_widget.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._msg_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        sublayout.addWidget(self._msg_widget)

        self._level_widget.addItems(list(QLogger._verbosity.keys()))
        self._level_widget.setEditable(False)
        self._level_widget.setCurrentText(self._level_widget.itemText(0))
        sublayout.addWidget(self._level_widget)

        layout.addLayout(sublayout)

        layout.addSpacing(24)

        # divider
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setMidLineWidth(3)
        layout.addWidget(hline)

        # add logger
        log_widget = QLogger(self.logger)
        log_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        layout.addWidget(log_widget)

        return layout

    @Slot()
    def enter_log(self):
        message = self._msg_widget.text()
        lvl_key = self._level_widget.currentText()
        level = QLogger._verbosity[lvl_key]

        self.logger.log(level=level, msg=message)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = DemoQLogger()
    window.show()

    app.exec()
