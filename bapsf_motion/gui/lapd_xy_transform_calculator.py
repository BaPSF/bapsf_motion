import ast
import re

from pathlib import Path
from PySide6.QtCore import Qt, QPoint, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QLineEdit,
)
from typing import Union

_HERE = Path(__file__).parent
_IMAGES_PATH = (_HERE / "_images").resolve()


class LaPDXYTransformCalculator(QMainWindow):
    def __init__(self):
        super().__init__()

        _stylesheet = self.styleSheet()
        _stylesheet += """
        QFrame#image_frame {
            border: 2px solid rgb(125, 125, 125);
            border-radius: 5px; 
            padding: 0px;
            margin: 0px;
            background-color: white;
        }
        
        QLineEdit { border: 2px solid black; border-radius: 5px }
        QLineEdit#measure_1 { border: 2px solid rgb(255, 0, 0) }
        QLineEdit#measure_2 { border: 2px solid rgb(255, 0, 0) }
        """
        self.setStyleSheet(_stylesheet)

        self._window_margin = 12
        self._define_main_window()
        self.setCentralWidget(QWidget(parent=self))

        self._image_file_path = (_IMAGES_PATH / "LaPDXYTransform_diagram.png").resolve()
        pixmap = QPixmap(f"{self._image_file_path}")
        self._image = pixmap.scaledToWidth(self.width() - 2 * self._window_margin)

        self.image_label = QLabel(parent=self)
        self.image_label.setPixmap(self._image)

        self.image_frame = QFrame(parent=self)
        self.image_frame.setObjectName("image_frame")
        self.image_frame.setStyleSheet(_stylesheet)
        self.image_frame.setFixedWidth(self.width() - 2 * self._window_margin)
        self.image_frame.setFixedHeight(self.height() - 2 * self._window_margin)

        self.ball_valve_cap_thickness = 0.81 * 2.54  # cm
        self.probe_drive_endplate_thickness = 0.75 * 2.54  # cm
        self.probe_kf40_thickness = 2.54  # cm
        self.velmex_rail_width = 3.4 * 2.54  # cm

        self.pivot_to_center = 58.771
        _txt = QLineEdit(f"{self.pivot_to_center:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(265, 48)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_center_label = _txt

        self.measure_1 = 54.2
        _txt = QLineEdit(f"{self.measure_1:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(778, 440)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_1")
        self.measure_1_label = _txt

        self.measure_2 = 58.0
        _txt = QLineEdit(f"{self.measure_2:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1250, 455)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_2")
        self.measure_2_label = _txt

        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        _txt = QLineEdit(f"{self.pivot_to_feedthru:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(750, 120)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_feedthru_label = _txt

        self.pivot_to_drive = self.calc_pivot_to_drive()
        _txt = QLineEdit(f"{self.pivot_to_drive:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1154, 48)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_drive_label = _txt

        layout = self._define_layout()
        self.centralWidget().setLayout(layout)

        self._connect_signals()

    def _define_main_window(self):
        self.setWindowTitle("LaPD XY Transform Calculator")
        height = 500
        width = int(3.52 * height)
        width += 2 * self._window_margin
        height += 2 * self._window_margin
        self.resize(width, height)
        self.setFixedWidth(width)
        self.setFixedHeight(height)

    def _connect_signals(self):
        self.measure_1_label.editingFinished.connect(self._validate_measure_1)
        self.measure_2_label.editingFinished.connect(self._validate_measure_2)

    def _define_layout(self):
        image_layout = QVBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_label)
        self.image_frame.setLayout(image_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(self.image_frame)
        layout.addStretch()
        return layout

    def calc_pivot_to_feedthru(self):
        return (
            self.ball_valve_cap_thickness
            + self.measure_1
            - self.probe_kf40_thickness
        )

    def calc_pivot_to_drive(self):
        return (
            self.ball_valve_cap_thickness
            + self.measure_1
            + self.probe_drive_endplate_thickness
            + self.measure_2
            + 0.5 * self.velmex_rail_width
        )

    def recalculate_parameters(self):
        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        self.pivot_to_drive = self.calc_pivot_to_drive()

        self._update_all_labels()

    def _update_all_labels(self):
        self._update_measure_1_label()
        self._update_measure_2_label()
        self._update_pivot_to_feedthru_label()
        self._update_pivot_to_drive_label()

    def _update_pivot_to_feedthru_label(self):
        _txt = f"{self.pivot_to_feedthru:.3f} cm"
        self.pivot_to_feedthru_label.setText(_txt)

    def _update_pivot_to_drive_label(self):
        _txt = f"{self.pivot_to_drive:.3f} cm"
        self.pivot_to_drive_label.setText(_txt)

    def _update_measure_1_label(self):
        _txt = f"{self.measure_1:.2f} cm"
        self.measure_1_label.setText(_txt)

    def _update_measure_2_label(self):
        _txt = f"{self.measure_2:.2f} cm"
        self.measure_2_label.setText(_txt)

    @staticmethod
    def _validate_measure(text: str) -> Union[float, None]:
        match = re.compile(r"(?P<value>\d+(.\d*)?)(\s*cm)?").fullmatch(text)

        if match is None:
            return None

        value = ast.literal_eval(match.group("value"))

        if value == 0:
            return None

        return float(value)

    @Slot()
    def _validate_measure_1(self):
        _txt = self.measure_1_label.text()
        value = self._validate_measure(_txt)

        if value is None:
            pass
        elif value <= self.probe_kf40_thickness:
            # not physically possible
            pass
        else:
            self.measure_1 = value
            self.recalculate_parameters()

        self._update_all_labels()

    @Slot()
    def _validate_measure_2(self):
        _txt = self.measure_2_label.text()
        value = self._validate_measure(_txt)

        if value is not None:
            self.measure_2 = value
            self.recalculate_parameters()

        self._update_all_labels()


class LaPDXYTransformCalculatorApp(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyle("Fusion")
        self.styleHints().setColorScheme(Qt.ColorScheme.Light)

        self._window = LaPDXYTransformCalculator()
        self._window.show()
        self._window.activateWindow()


if __name__ == "__main__":
    app = LaPDXYTransformCalculatorApp([])
    app.exec()
