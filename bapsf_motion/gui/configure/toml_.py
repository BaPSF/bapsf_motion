__all__ = ["TOMLText"]

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QAbstractScrollArea


class TOMLText(QPlainTextEdit):

    def __init__(
        self,
        text: str = "",
        /,
        parent: QWidget | None = None,
    ):

        super().__init__(text, parent=parent)

        self.setReadOnly(True)
        font = self.font()
        font.setPointSize(10)
        font.setFamily("Courier New")
        self.setFont(font)

