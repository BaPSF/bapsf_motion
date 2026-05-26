__all__ = ["WarningMessageBox"]

from PySide6.QtWidgets import QMessageBox, QWidget
from typing import Union


class WarningMessageBox(QMessageBox):
    """
    A generical modal warning dialog box to dispaly arbitrary warning
    messages.
    """

    def __init__(self, message: str, parent: Union[QWidget, None] = None):
        super().__init__(parent)

        self.setWindowTitle("!! WARNING !!")
        self.setIcon(QMessageBox.Icon.Warning)
        self.setStandardButtons(QMessageBox.StandardButton.Ok)
        self.setDefaultButton(QMessageBox.StandardButton.Ok)

        # define font size for warning text
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        self.setText(message)
