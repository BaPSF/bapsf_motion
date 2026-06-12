"""
Module containg custom `QDialog` and `QMessageBox` classes.
"""

__all__ = [
    "LostConnectionMessageBox",
    "MSpaceMessageBox",
    "WarningMessageBox",
]

from pathlib import Path
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget, QCheckBox

_HERE = Path(__file__).parent


class WarningMessageBox(QMessageBox):
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

        self.setWindowTitle("!! WARNING !!")
        self._place_window_icon()
        self.setIcon(QMessageBox.Icon.Warning)

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

    def _place_window_icon(self):
        _image_name = "BaPSF_Logo_Color_yellow_background_RGB_32px.ico"
        _image_root_path = (_HERE / ".." / "_images").resolve()
        _image_path = (_image_root_path / _image_name).resolve()

        if not _image_path.exists() or not _image_path.is_file():
            # do nothing, the image file can not be located
            return

        self.setWindowIcon(QIcon(f"{_image_path}"))

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


class LostConnectionMessageBox(QMessageBox):
    """
    Modal warning dialog box to warn the user that the TCP connection
    to a physical motor was lost.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._display_dialog = True

        self.setWindowTitle("Lost TCP Connection to Motor")
        self._base_message = "Lost TCP connection to physical motor."
        self._lost_motors = {}
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        self.setText(self._base_message)

        self.setIcon(QMessageBox.Icon.Warning)
        self.setStandardButtons(QMessageBox.StandardButton.Discard)
        self.setDefaultButton(QMessageBox.StandardButton.Discard)

    @property
    def display_dialog(self) -> bool:
        return self._display_dialog

    @display_dialog.setter
    def display_dialog(self, value: bool) -> None:
        if not isinstance(value, bool):
            return

        self._display_dialog = value

    def _update_display_dialog(self) -> None:
        if len(self._lost_motors) == 0:
            self.setText(self._base_message)

            if self.isVisible():
                self.defaultButton().click()
            return None

        msg = self._base_message + "\n\n"
        for name, ip in self._lost_motors.items():
            msg += f"    {name} : {ip}\n"

        self.setText(msg)

        if not self.isVisible():
            self.exec()

        return None

    def register_lost_motor(self, name: str, ip: str) -> None:
        if name in self._lost_motors:
            return

        self._lost_motors[name] = ip
        self._update_display_dialog()

    def register_resolved_motor(self, name):
        if name not in self._lost_motors:
            return

        self._lost_motors.pop(name)
        self._update_display_dialog()

    def exec(self) -> bool:
        if not self.display_dialog:
            return True

        if not self.isEnabled():
            return True

        super().exec()

        return True


class MSpaceMessageBox(QMessageBox):
    """
    Modal warning dialog box to warn the user the motion space has yet
    to be defined.  Thus, there are no restrictions on probe drive
    movement, and it is up to the user to prevent any collisions.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)

        self._display_dialog = True

        self.setWindowTitle("Motion Space NOT Defined")
        self.setText(
            "Motion Space is NOT defined, so there are no restrictions "
            "on probe drive motion.  It is up to the user to avoid "
            "collisions.\n\n"
            "Proceed with movement?"
        )
        self.setIcon(QMessageBox.Icon.Warning)
        self.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Abort
        )
        self.setDefaultButton(QMessageBox.StandardButton.Abort)

        _cb = QCheckBox("Suppress future warnings for this motion group.")
        self.setCheckBox(_cb)

        self.checkBox().checkStateChanged.connect(self._update_display_dialog)

    @property
    def display_dialog(self) -> bool:
        return self._display_dialog

    @display_dialog.setter
    def display_dialog(self, value: bool) -> None:
        if not isinstance(value, bool):
            return

        # ensure the display boolean (display_dialog) is in sync
        # with the dialog check box ... these two values are supposed
        # to be NOTs of each other
        check_state = self.checkBox().checkState()
        if check_state is Qt.CheckState.Checked is value:
            self.checkBox().setChecked(not value)

        self._display_dialog = value

    @Slot(Qt.CheckState)
    def _update_display_dialog(self, state: Qt.CheckState) -> None:
        self.display_dialog = not (state is Qt.CheckState.Checked)

    def exec(self) -> bool:
        if not self.display_dialog:
            return True

        button = super().exec()

        if button == QMessageBox.StandardButton.Yes:
            # Make sure the Abort button always remains the default choice
            self.setDefaultButton(QMessageBox.StandardButton.Abort)
            return True
        elif button == QMessageBox.StandardButton.Abort:
            return False

        return False
