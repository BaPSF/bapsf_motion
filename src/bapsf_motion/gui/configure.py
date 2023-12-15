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

from bapsf_motion.gui.widgets import QLogger, StyleButton


class RunWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.done_btn = StyleButton("DONE")
        self.done_btn.setFixedWidth(200)
        self.done_btn.setFixedHeight(48)
        font = self.done_btn.font()
        font.setPointSize(24)
        self.done_btn.setFont(font)

        self.quit_btn = StyleButton("Discard && Quit")
        self.quit_btn.setFixedWidth(200)
        self.quit_btn.setFixedHeight(48)
        font = self.done_btn.font()
        font.setPointSize(24)
        font.setBold(True)
        self.quit_btn.setFont(font)
        self.quit_btn.update_style_sheet(
            {"background-color": "rgb(255, 110, 110)"}
        )

        self.import_btn = StyleButton("IMPORT")
        self.import_btn.setFixedHeight(28)
        font = self.import_btn.font()
        font.setPointSize(16)
        self.import_btn.setFont(font)

        self.export_btn = StyleButton("EXPORT")
        self.export_btn.setFixedHeight(28)
        font = self.export_btn.font()
        font.setPointSize(16)
        self.export_btn.setFont(font)

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
        toml_widget = QWidget()
        toml_widget.setLayout(self._define_toml_layout())
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

    def _define_toml_layout(self):
        layout = QGridLayout()
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

        layout.addWidget(label, 0, 0, 1, 2)
        layout.addWidget(self.config_widget, 1, 0, 1, 2)
        layout.addWidget(self.import_btn, 2, 0, 1, 1)
        layout.addWidget(self.export_btn, 2, 1, 1, 1)

        return layout


class ConfigureGUI(QMainWindow):

    def __init__(self):
        super().__init__()

        # setup logger
        logging.config.dictConfig(self._logging_config_dict)
        self._logger = logging.getLogger(":: GUI ::")

        self._define_main_window()

        # define "important" qt widgets
        self._log_widget = QLogger(self._logger)
        self._run_widget = RunWidget()

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

        # layout.addWidget(self.dummy_widget())
        layout.addWidget(self._run_widget)

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
