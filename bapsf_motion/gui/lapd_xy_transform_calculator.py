__all__ = ["LaPDXYTransformCalculator", "LaPDXYTransformCalculatorApp"]

import ast
import re

from pathlib import Path
from PySide6.QtCore import Qt, QPoint, Signal, Slot
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
    QRadioButton,
)
from typing import Union, Optional

from bapsf_motion.gui.widgets import StyleButton


_HERE = Path(__file__).parent
_IMAGES_PATH = (_HERE / "_images").resolve()


class LaPDXYTransformCalculator(QMainWindow):
    closing = Signal()

    _defaults = {  # all values in cm
        "measure_1": 54.2,
        "measure_2a": 58.0,
    }

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
        QLineEdit#measure_2a { border: 2px solid rgb(255, 0, 0) }
        QLineEdit#measure_2b { border: 2px solid rgb(255, 0, 0) }
        
        QLineEdit#ball_valve_cap_thickness {
            border: 2px solid rgb(68, 114, 196);
            color: rgb(68, 114, 196);
        }
        QLineEdit#probe_kf40_thickness {
            border: 2px solid rgb(68, 114, 196);
            color: rgb(68, 114, 196);
        }
        QLineEdit#probe_drive_endplate_thickness {
            border: 2px solid rgb(68, 114, 196);
            color: rgb(68, 114, 196);
        }
        QLineEdit#velmex_rail_width {
            border: 2px solid rgb(68, 114, 196);
            color: rgb(68, 114, 196);
        }
        QLineEdit#fiducial_width {
            border: 2px solid rgb(68, 114, 196);
            color: rgb(68, 114, 196);
        }
        """
        self.setStyleSheet(_stylesheet)

        self.setCentralWidget(QWidget(parent=self))

        self._image_file_path = (_IMAGES_PATH / "LaPDXYTransform_diagram.png").resolve()
        pixmap = QPixmap(f"{self._image_file_path}")
        self._image = pixmap

        self._window_margin = 12
        self._define_main_window()

        self.image_label = QLabel(parent=self)
        self.image_label.setPixmap(self._image)

        self.image_frame = QFrame(parent=self)
        self.image_frame.setObjectName("image_frame")
        self.image_frame.setStyleSheet(_stylesheet)
        self.image_frame.setFixedWidth(self.width() - 2 * self._window_margin)
        self.image_frame.setFixedHeight(self.height() - 2 * self._window_margin)

        # all values in cm
        self.ball_valve_cap_thickness = 0.81 * 2.54
        self.probe_drive_endplate_thickness = 0.75 * 2.54
        self.probe_kf40_thickness = 2.54
        self.velmex_rail_width = 3.4 * 2.54
        self.fiducial_width = 1.775 * 2.54

        # constants need to be defined first
        self.measure_1 = self._defaults["measure_1"]
        self.measure_2a = self._defaults["measure_2a"]
        self.measure_2b = self.convert_measure_2a_to_measure_2b()

        # mesures and constants need to be defined first
        self.pivot_to_center = 58.771
        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        self.pivot_to_drive = self.calc_pivot_to_drive()

        _txt = QLineEdit(f"{self.pivot_to_center:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(260, 43)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_center_label = _txt

        _txt = QLineEdit(f"{self.measure_1:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(763, 432)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_1")
        self.measure_1_label = _txt

        _txt = QLineEdit(f"{self.measure_2a:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1228, 447)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_2a")
        self.measure_2a_label = _txt

        _txt = QLineEdit(f"{self.measure_2b:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1228, 499)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_2b")
        self.measure_2b_label = _txt
        self.measure_2b_label.setEnabled(False)

        _txt = QLineEdit(f"{self.pivot_to_feedthru:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(736, 98)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_feedthru_label = _txt

        _txt = QLineEdit(f"{self.pivot_to_drive:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1134, 43)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_drive_label = _txt

        _txt = QLineEdit(f"{self.ball_valve_cap_thickness:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(691, 181)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("ball_valve_cap_thickness")
        self.ball_valve_cap_thickness_label = _txt

        _txt = QLineEdit(f"{self.probe_kf40_thickness:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1218, 177)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("probe_kf40_thickness")
        self.probe_kf40_thickness_label = _txt

        _txt = QLineEdit(f"{self.probe_drive_endplate_thickness:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1294, 220)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("probe_drive_endplate_thickness")
        self.probe_drive_endplate_thickness_label = _txt

        _txt = QLineEdit(f"{self.velmex_rail_width:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1496, 121)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("velmex_rail_width")
        self.velmex_rail_width_label = _txt

        _txt = QLineEdit(f"{self.fiducial_width:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1774, 512)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("fiducial_width")
        self.fiducial_width_label = _txt

        _btn = StyleButton("Reset to Defaults", parent=self)
        _btn.setFixedWidth(200)
        _btn.setFixedHeight(36)
        _btn.setPointSize(14)
        p = self.geometry().topLeft() + QPoint(32, 472)
        _btn.move(p)
        self.reset_btn = _btn

        _btn = QRadioButton(parent=self)
        p = self.measure_2a_label.pos() + QPoint(self.measure_2a_label.width() + 6, 0)
        _btn.move(p)
        _btn.setChecked(True)
        self.measure_2a_btn = _btn

        _btn = QRadioButton(parent=self)
        p = self.measure_2b_label.pos() + QPoint(self.measure_2b_label.width() + 6, 0)
        _btn.move(p)
        self.measure_2b_btn = _btn

        layout = self._define_layout()
        self.centralWidget().setLayout(layout)

        self._connect_signals()

    def _define_main_window(self):
        self.setWindowTitle("LaPD XY Transform Calculator")
        width = self._image.width() + 2 * self._window_margin
        height = self._image.height() + 2 * self._window_margin
        self.resize(width, height)
        self.setFixedWidth(width)
        self.setFixedHeight(height)

    def _connect_signals(self):
        self.measure_1_label.editingFinished.connect(self._validate_measure_1)
        self.measure_2a_label.editingFinished.connect(self._validate_measure_2a)
        self.measure_2b_label.editingFinished.connect(self._validate_measure_2b)

        self.reset_btn.clicked.connect(self._reset_measure_values)

        self.measure_2a_btn.toggled.connect(self._measure_2a_input_selected)
        self.measure_2b_btn.toggled.connect(self._measure_2b_input_selected)

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

    def convert_measure_2a_to_measure_2b(
        self, measure_2a: Optional[float] = None
    ) -> float:
        if measure_2a is None:
            measure_2a = self.measure_2a

        return measure_2a + self.velmex_rail_width + self.fiducial_width

    def convert_measure_2b_to_measure_2a(
        self, measure_2b: Optional[float] = None
    ) -> float:
        if measure_2b is None:
            measure_2b = self.measure_2b

        return measure_2b - self.velmex_rail_width - self.fiducial_width

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
            + self.measure_2a
            + 0.5 * self.velmex_rail_width
        )

    def recalculate_parameters(self):
        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        self.pivot_to_drive = self.calc_pivot_to_drive()

        self._update_all_labels()

    def _measure_2a_input_selected(self):
        self.measure_2a_label.setEnabled(True)
        self.measure_2b_label.setEnabled(False)

    def _measure_2b_input_selected(self):
        self.measure_2a_label.setEnabled(False)
        self.measure_2b_label.setEnabled(True)

    def _reset_measure_values(self):
        self.measure_1 = self._defaults["measure_1"]
        self.measure_2a = self._defaults["measure_2a"]
        self.measure_2b = self.convert_measure_2a_to_measure_2b()

        self.recalculate_parameters()

    def _update_all_labels(self):
        self._update_measure_1_label()
        self._update_measure_2a_label()
        self._update_measure_2b_label()
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

    def _update_measure_2a_label(self):
        _txt = f"{self.measure_2a:.2f} cm"
        self.measure_2a_label.setText(_txt)

    def _update_measure_2b_label(self):
        _txt = f"{self.measure_2b:.2f} cm"
        self.measure_2b_label.setText(_txt)

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
            return

        self._update_all_labels()

    @Slot()
    def _validate_measure_2a(self):
        _txt = self.measure_2a_label.text()
        value = self._validate_measure(_txt)

        if value is None:
            pass
        elif value <= 0:
            # not physically possible
            pass
        else:
            self.measure_2a = value
            self.measure_2b = self.convert_measure_2a_to_measure_2b()
            self.recalculate_parameters()
            return

        self._update_all_labels()

    @Slot()
    def _validate_measure_2b(self):
        _txt = self.measure_2b_label.text()
        value = self._validate_measure(_txt)

        if value is None:
            pass
        elif value <= self.velmex_rail_width + self.fiducial_width:
            # not physically possible
            pass
        else:
            self.measure_2b = value
            self.measure_2a = self.convert_measure_2b_to_measure_2a()
            self.recalculate_parameters()
            return

        self._update_all_labels()

    def closeEvent(self, event):
        self.closing.emit()
        super().closeEvent(event)


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
