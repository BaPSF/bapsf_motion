from __future__ import annotations

__all__ = ["AxisPositionWarningDialog", "WarningMessageBox"]

import logging

from pathlib import Path
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QWidget,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
)
from typing import TYPE_CHECKING

from bapsf_motion.actors import Axis, Motor
from bapsf_motion.gui.configure.helpers import gui_logger
from bapsf_motion.gui.widgets import DoneButton

if TYPE_CHECKING:
    from bapsf_motion.gui.configure.motion_group_widget import AxisControlWidget

_HERE = Path(__file__).parent
_IMAGE_ROOT_PATH = (_HERE / ".." / "_images").resolve()


class _BaseWarningDialog(QDialog):
    _IMAGE_ROOT_PATH = _IMAGE_ROOT_PATH
    _ICON_NAME = "BaPSF_Logo_Color_yellow_background_RGB_32px.ico"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("!!!  WARNING  !!!")
        self._set_window_icon()

    def _set_window_icon(self):
        _image_path = (self._IMAGE_ROOT_PATH / self._ICON_NAME).resolve()

        if not _image_path.exists() or not _image_path.is_file():
            # do nothing, the image file can not be located
            return

        self.setWindowIcon(QIcon(f"{_image_path}"))


class _BaseWarningMessageBox(QMessageBox):
    _IMAGE_ROOT_PATH = _IMAGE_ROOT_PATH
    _ICON_NAME = "BaPSF_Logo_Color_yellow_background_RGB_32px.ico"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("!!!  WARNING  !!!")
        self._set_window_icon()
        self.setIcon(QMessageBox.Icon.Warning)

    def _set_window_icon(self):
        _image_path = (self._IMAGE_ROOT_PATH / self._ICON_NAME).resolve()

        if not _image_path.exists() or not _image_path.is_file():
            # do nothing, the image file can not be located
            return

        self.setWindowIcon(QIcon(f"{_image_path}"))


class WarningMessageBox(_BaseWarningMessageBox):
    """
    A generical modal warning dialog box to display arbitrary warning
    messages.

    Parameters
    ----------
    message : `str`
        Message to be displayed in the dialog box.

    button_layout : `str`
        (DEFAULT: ``"acknowledge"``) A string of ``"acknowledge"`` or
        ``"approve"`` indicates the button layout.  If
        ``"acknowledge"``, then only an OK button is displayed for the
        user to acknowledge the warning.  If ``"approve"``, then a YES
        and NO button is displayed and the user must choose how to
        proceed.

    parent : QWidget | None
        The parent / owning widget.
    """

    def __init__(
        self,
        message: str,
        button_layout: str = "acknowledge",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        # create button layout
        if not isinstance(button_layout, str):
            raise TypeError(
                "Argument 'button_layout' must be a string in "
                "{'acknowledge', 'approve'}, but got type "
                f"{type(button_layout)}."
            )
        self._button_layout = button_layout

        if button_layout == "acknowledge":
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
            self.setDefaultButton(QMessageBox.StandardButton.Ok)
        elif button_layout == "approve":
            self.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            self.setDefaultButton(QMessageBox.StandardButton.No)
        else:
            raise ValueError(
                "Argument 'button_layout' must be a string in "
                "{'acknowledge', 'approve'}, but got value "
                f"'{button_layout}'."
            )

        # define font size for warning text
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        if button_layout == "approve":
            message += "\n\nDo you want to proceed?"
        self.setText(message)

    def _acknowledge_exec(self, /) -> int:
        return super().exec()

    def _approve_exec(self, /) -> int:
        button = super().exec()
        if button == QMessageBox.StandardButton.Yes:
            # Make sure the Abort button always remains the default choice
            self.setDefaultButton(QMessageBox.StandardButton.No)
            return QDialog.DialogCode.Accepted

        return QDialog.DialogCode.Rejected

    def exec(self, /) -> int:
        if self._button_layout == "acknowledge":
            return self._acknowledge_exec()

        return self._approve_exec()


class AxisPositionWarningDialog(_BaseWarningDialog):

    def __init__(self, axis_control_widget: AxisControlWidget, parent: QWidget | None = None):
        super().__init__(parent)

        self._acw = axis_control_widget
        self._display_dialog = True
        self._logger = logging.getLogger(f"{gui_logger.name}.APWD")

        self.setModal(True)

        _btn = DoneButton("FINISHED", parent=self)
        _btn.setFixedHeight(24)
        font = _btn.font()
        font.setPointSize(14)
        _btn.setFont(font)
        _btn.shrink_width()
        self.finished_btn = _btn

        _cb = QCheckBox(
            "Suppress future warnings for this axis.",
            parent=self,
        )
        font = _cb.font()
        font.setPointSize(14)
        _cb.setFont(font)
        self.suppression_checkbox = _cb

        self.setLayout(self._define_layout())
        self._connect_signals()

    def _connect_signals(self) -> None:
        self.suppression_checkbox.checkStateChanged.connect(self._update_display_dialog)
        self.finished_btn.clicked.connect(self._handle_finished_btn_clicked)

    def _define_layout(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.suppression_checkbox)
        layout.addSpacing(12)
        layout.addWidget(self.finished_btn)
        return layout

    @property
    def acw(self) -> AxisControlWidget:
        return self._acw

    @property
    def axis(self) -> Axis:
        return self.acw.axis

    @property
    def display_dialog(self) -> bool:
        return self._display_dialog

    @display_dialog.setter
    def display_dialog(self, value: bool) -> None:
        if not isinstance(value, bool):
            return

        self._display_dialog = value

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @Slot()
    def _handle_finished_btn_clicked(self) -> None:
        self.blockSignals(True)
        self.display_dialog = False
        self.suppression_checkbox.setChecked(True)
        self.blockSignals(False)

        self.close()

    @Slot(Qt.CheckState)
    def _update_display_dialog(self, state: Qt.CheckState) -> None:
        self.display_dialog = not (state is Qt.CheckState.Checked)

    def exec(self, /):
        if not self.display_dialog:
            return

        if not isinstance(self.axis, Axis):
            # this dialog is only meaningful is we have an operating Axis actor
            return

        super().exec()

    def open(self, /):
        if not self.display_dialog:
            return

        if not isinstance(self.axis, Axis):
            # this dialog is only meaningful is we have an operating Axis actor
            return

        super().open()

    def closeEvent(self, event: QCloseEvent, /):
        super().closeEvent(event)
