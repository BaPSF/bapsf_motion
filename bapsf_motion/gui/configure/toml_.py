__all__ = ["TOMLSyntaxHighlighter", "TOMLText"]

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QPalette,
    QTextDocument,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class TOMLSyntaxHighlighter(QSyntaxHighlighter):

    def __init__(self, document: QTextDocument):
        super().__init__(document)

        # Formats
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor('#898887'))
        comment_format.setFontItalic(True)

        key_format = QTextCharFormat()
        key_format.setForeground(QColor('#0057ae'))
        key_format.setFontWeight(QFont.Weight.Bold)

        table_format = QTextCharFormat()
        table_format.setForeground(QColor('#1f1c1b'))
        table_format.setFontWeight(QFont.Weight.Bold)

        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#bf0303'))

        value_format = QTextCharFormat()
        value_format.setForeground(QColor('#b08000'))

        # Rules mapping (Regex -> Format)
        self.rules = {
            "comment": (
                QRegularExpression(r"#[^\n]*"),
                comment_format,
            ),  # Comments (# ...)
            "table": (
                QRegularExpression(r"^\s*\[{1,2}.*?\]{1,2}"),
                table_format,
            ),  # Tables ([table] or [[tablearray]])
            "key": (
                QRegularExpression(r"^\s*[\w.-]+\s*(?==)"),
                key_format,
            ),  # keys (word before =)
            "string": (
                QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"|\'[^\']*\''),
                string_format,
            ),  # strings ("..." or '...')
            "value": (
                QRegularExpression(r"\b(true|false|\d[\d_]*(?:\.\d[\d_]*)?)\b"),
                value_format,
            ),  # Numbers and Booleans
        }

    def highlightBlock(self, text: str):
        for content_name, content_value in self.rules.items():
            content_pattern, content_format = content_value
            match_iterator = content_pattern.globalMatch(text)
            set_format = False
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), content_format
                )

                if (
                    content_name == "table"
                    and match.capturedStart() == 0
                    and match.capturedEnd() == len(text)
                ):
                    set_format = True
                    break

                if content_name == "string" and match.capturedEnd() == len(text):
                    set_format = True
                    break

            if set_format:
                return


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

