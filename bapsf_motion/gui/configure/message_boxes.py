__all__ = ["WarningMessageBox"]

from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

_HERE = Path(__file__).parent


class _BaseWarningMessageBox(QMessageBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowTitle("!!!  WARNING  !!!")
        self._place_window_icon()
        self.setIcon(QMessageBox.Icon.Warning)

    def _place_window_icon(self):
        _image_name = "BaPSF_Logo_Color_yellow_background_RGB_32px.ico"
        _image_root_path = (_HERE / ".." / "_images").resolve()
        _image_path = (_image_root_path / _image_name).resolve()

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
