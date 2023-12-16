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
    QLineEdit,
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

        self.add_mg_btn = StyleButton("ADD")
        self.add_mg_btn.setFixedHeight(32)
        font = self.add_mg_btn.font()
        font.setPointSize(16)
        self.add_mg_btn.setFont(font)

        self.remove_mg_btn = StyleButton("REMOVE")
        self.remove_mg_btn.setFixedHeight(32)
        font = self.remove_mg_btn.font()
        font.setPointSize(16)
        self.remove_mg_btn.setFont(font)

        self.modify_mg_btn = StyleButton("Edit / Control")
        self.modify_mg_btn.setFixedHeight(32)
        font = self.modify_mg_btn.font()
        font.setPointSize(16)
        self.modify_mg_btn.setFont(font)

        self.config_widget = QTextEdit()
        self.mg_list_widget = QListWidget()

        self.run_name_widget = QLineEdit()
        font = self.run_name_widget.font()
        font.setPointSize(16)
        self.run_name_widget.setFont(font)

        self.setLayout(self._define_layout())

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
