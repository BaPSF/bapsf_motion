import logging
import logging.config

from pathlib import Path
from PySide6.QtCore import Qt, QDir, Signal
from PySide6.QtGui import QCloseEvent
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
)
from typing import Any, Dict, Union

from bapsf_motion.actors import RunManager
from bapsf_motion.gui.widgets import QLogger, StyleButton
from bapsf_motion.utils import toml


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
        self.add_mg_btn.setEnabled(False)

        self.remove_mg_btn = StyleButton("REMOVE")
        self.remove_mg_btn.setFixedHeight(32)
        font = self.remove_mg_btn.font()
        font.setPointSize(16)
        self.remove_mg_btn.setFont(font)
        self.remove_mg_btn.setEnabled(False)

        self.modify_mg_btn = StyleButton("Edit / Control")
        self.modify_mg_btn.setFixedHeight(32)
        font = self.modify_mg_btn.font()
        font.setPointSize(16)
        self.modify_mg_btn.setFont(font)
        self.modify_mg_btn.setEnabled(False)

        self.config_widget = QTextEdit()
        self.mg_list_widget = QListWidget()

        self.run_name_widget = QLineEdit()
        font = self.run_name_widget.font()
        font.setPointSize(16)
        self.run_name_widget.setFont(font)

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


class ConfigureGUI(QMainWindow):
    _OPENED_FILE = None # type: Union[Path, None]
    configChanged = Signal()

    def __init__(self):
        super().__init__()

        self._rm = None

        # setup logger
        logging.config.dictConfig(self._logging_config_dict)
        self._logger = logging.getLogger(":: GUI ::")
        self._rm_logger = logging.getLogger("RM")

        self._define_main_window()

        # define "important" qt widgets
        self._log_widget = QLogger(self._logger)
        self._run_widget = RunWidget()

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

    def _connect_signals(self):
        self._run_widget.import_btn.clicked.connect(self.import_file)
        self._run_widget.done_btn.clicked.connect(self.save_and_close)
        self._run_widget.quit_btn.clicked.connect(self.close)

        self._run_widget.run_name_widget.editingFinished.connect(self.change_run_name)

        self.configChanged.connect(self.update_display_config_text)
        self.configChanged.connect(self.update_display_rm_name)
        self.configChanged.connect(self.update_display_mg_list)

    def closeEvent(self, event: "QCloseEvent") -> None:
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


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    window = ConfigureGUI()
    window.show()

    app.exec()
