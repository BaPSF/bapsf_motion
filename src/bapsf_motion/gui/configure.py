import logging
import logging.config

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QFrame,
    QPushButton,
    QTextEdit,
    QListWidget,
    QVBoxLayout,
)
from typing import Any, Dict

from bapsf_motion.gui.widgets import QLogger


class RunWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.done_btn = QPushButton("DONE")
        self.quit_btn = QPushButton("Discard & Quit")

        self.import_btn = QPushButton("IMPORT")
        self.export_btn = QPushButton("EXPORT")
        self.add_mg_btn = QPushButton("ADD")
        self.remove_mg_btn = QPushButton("REMOVE")
        self.modify_mg_btn = QPushButton("Edit / Control")

        self.config_widget = QTextEdit()
        self.mg_list_widget = QListWidget()

        self.setLayout(self._define_layout())

    def _define_layout(self):
        main_layout = QVBoxLayout()

        # Create layout for top buttons
        top_btn_layout = QHBoxLayout()
        top_btn_layout.addWidget(self.quit_btn)
        top_btn_layout.addStretch()
        top_btn_layout.addWidget(self.done_btn)

        # Create layout for toml window
        toml_layout = QGridLayout()
        label = QLabel("Run Configuration")
        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom
        )
        label.font().setPointSize(12)

        self.config_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        self.config_widget.setReadOnly(True)
        self.config_widget.font().setPointSize(14)
        self.config_widget.font().setFamily("Courier New")

        toml_layout.addWidget(label, 0, 0, 1, 2)
        toml_layout.addWidget(self.config_widget, 1, 0, 1, 2)
        toml_layout.addWidget(self.import_btn, 2, 0, 1, 1)
        toml_layout.addWidget(self.export_btn, 2, 1, 1, 1)

        toml_widget = QWidget()
        toml_widget.setLayout(toml_layout)
        toml_widget.setMinimumWidth(400)
        toml_widget.setMinimumWidth(500)
        toml_widget.sizeHint().setWidth(450)

        # Create layout for

        # Construct layout below top buttons
        layout = QHBoxLayout()
        layout.addWidget(toml_widget)
        layout.addStretch()

        # Populate the main layout
        main_layout.addLayout(top_btn_layout)
        main_layout.addLayout(layout)

        return main_layout


class ConfigureGUI(QMainWindow):

    def __init__(self):
        super().__init__()

        logging.config.dictConfig(self._logging_config_dict)
        self._logger = logging.getLogger(":: GUI ::")

        self._log_widget = QLogger(self._logger)

        self._define_main_window()

        layout = self._define_layout()

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

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

    def _define_main_window(self):
        self.setWindowTitle("Run Configuration")
        self.resize(1760, 990)
        self.setMinimumHeight(600)

    def _define_layout(self):
        layout = QHBoxLayout()

        layout.addWidget(self.dummy_widget())

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

    def dummy_layout(self):
        layout = QGridLayout()
        layout.addWidget(QLabel("Dummy Widget"), 0, 0)

        return layout

    def dummy_widget(self):
        widget = QWidget()
        widget.setLayout(self.dummy_layout())

        return widget


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
