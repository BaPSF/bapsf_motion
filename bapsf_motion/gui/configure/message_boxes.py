__all__ = ["WarningMessageBox"]

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from typing import Union


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

    parent : Union[QWidget, None]
        The parent / owning widget.
    """

    def __init__(
        self,
        message: str,
        button_layout: str = "acknowledge",
        parent: Union[QWidget, None] = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("!! WARNING !!")
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
