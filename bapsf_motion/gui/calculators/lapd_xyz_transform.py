__all__ = ["LaPDXYZTransformCalculator", "LaPDXYZTransformCalculatorApp"]

import ast
import re

from PySide6.QtCore import Qt, QPoint, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QLineEdit,
    QRadioButton,
)
from typing import Union, Optional

from bapsf_motion.gui.calculators.bases import BaseCalculatorWindow, BaseCalculatorApp
from bapsf_motion.gui.widgets import StyleButton


class LaPDXYZTransformCalculator(BaseCalculatorWindow):
    _WINDOW_TITLE = "LaPD XYZ Calculator"
    _IMAGE_NAME = "LaPDXYZTransform_diagram.png"

    _defaults = {  # all values in cm
        "measure_1": 54.2,
        "measure_2": 58.0,
    }

    def __init__(self):

        # Initialized measure values
        self.measure_1 = self._defaults["measure_1"]
        self.measure_2 = self._defaults["measure_2"]

        # Initialized constants
        self.ball_valve_cap_thickness = 0.81 * 2.54
        self.probe_drive_endplate_thickness = 0.75 * 2.54
        self.probe_kf40_thickness = 2.54
        self.velmex_rail_width = 3.4 * 2.54

        # Initilized "Calculated" Transform Parameters
        self.pivot_to_center = 58.771
        self.probe_axis_offset = 30.47
        self.table_pivot_to_zlead_screw = 12.488
        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        self.pivot_to_xzcross = self.calc_pivot_to_xzcross()

        super().__init__()

    def _init_widgets(self):
        # Place "measure" labels
        _txt = QLineEdit(f"{self.measure_1:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(598, 442)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_1")
        self.measure_1_label = _txt

        _txt = QLineEdit(f"{self.measure_2:.2f} cm", parent=self)
        _txt.setReadOnly(False)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1050, 508)
        _txt.move(p)
        _txt.setFixedWidth(120)
        _txt.setObjectName("measure_2")
        self.measure_2_label = _txt

        # Place "constant" labels
        _txt = QLineEdit(f"{self.ball_valve_cap_thickness:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(12)
        font.setBold(True)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(526, 191)
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
        p = self.geometry().topLeft() + QPoint(1053, 187)
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
        p = self.geometry().topLeft() + QPoint(1129, 230)
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
        p = self.geometry().topLeft() + QPoint(1496 - 273, 121 + 24)
        _txt.move(p)
        _txt.setFixedWidth(86)
        _txt.setObjectName("velmex_rail_width")
        self.velmex_rail_width_label = _txt

        # Place "Transform Parameter" labels
        _txt = QLineEdit(f"{self.pivot_to_center:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(262, 17)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_center_label = _txt

        _txt = QLineEdit(f"{self.pivot_to_feedthru:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(570, 108)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_feedthru_label = _txt

        _txt = QLineEdit(f"{self.probe_axis_offset:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1590, 658)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.probe_axis_offset_label = _txt

        _txt = QLineEdit(f"{self.pivot_to_xzcross:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(980, 17)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.pivot_to_xzcross_label = _txt

        _txt = QLineEdit(f"{self.table_pivot_to_zlead_screw:.3f} cm", parent=self)
        _txt.setReadOnly(True)
        _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = _txt.font()
        font.setPointSize(14)
        _txt.setFont(font)
        p = self.geometry().topLeft() + QPoint(1437, 82)
        _txt.move(p)
        _txt.setFixedWidth(120)
        self.table_pivot_to_zlead_screw_label = _txt

        # Place Action Buttons
        p = self.geometry().topLeft() + QPoint(270, 694)
        self.reset_btn.move(p)

        p += QPoint(220, 0)
        self.export_btn.move(p)

    def _connect_signals(self):
        self.measure_1_label.editingFinished.connect(self._validate_measure_1)
        self.measure_2_label.editingFinished.connect(self._validate_measure_2)

    @property
    def _stylesheet_string(self):
        _stylesheet = super()._stylesheet_string
        _stylesheet += """
        QLineEdit { border: 2px solid black; border-radius: 5px }
        QLineEdit#measure_1 { border: 2px solid rgb(255, 0, 0) }
        QLineEdit#measure_2 { border: 2px solid rgb(255, 0, 0) }
        
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
        """
        return _stylesheet

    def calc_pivot_to_feedthru(self):
        return (
            self.ball_valve_cap_thickness
            + self.measure_1
            - self.probe_kf40_thickness
        )

    def calc_pivot_to_xzcross(self):
        return (
            self.ball_valve_cap_thickness
            + self.measure_1
            + self.probe_drive_endplate_thickness
            + self.measure_2
            + self.table_pivot_to_zlead_screw
        )

    def recalculate_parameters(self):
        self.pivot_to_feedthru = self.calc_pivot_to_feedthru()
        self.pivot_to_xzcross = self.calc_pivot_to_xzcross()

        self._update_all_labels()

    def _reset_measure_values(self):
        self.measure_1 = self._defaults["measure_1"]
        self.measure_2 = self._defaults["measure_2"]

        self.recalculate_parameters()

    @Slot()
    def _reset_parameters(self):
        self._reset_measure_values()

    def _update_all_labels(self):
        # No update of
        #
        #  - pivot_to_center_label
        #  - probe_axis_offset_label
        #  - table_pivot_to_zlead_screw_label
        #
        # is needed because they do NOT change with measure_1
        # and measure_2
        #
        self._update_measure_1_label()
        self._update_measure_2_label()
        self._update_pivot_to_feedthru_label()
        self._update_pivot_to_xzcross_label()

    def _update_pivot_to_feedthru_label(self):
        _txt = f"{self.pivot_to_feedthru:.3f} cm"
        self.pivot_to_feedthru_label.setText(_txt)

    def _update_pivot_to_xzcross_label(self):
        _txt = f"{self.pivot_to_xzcross:.3f} cm"
        self.pivot_to_xzcross_label.setText(_txt)

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

        if (
            value is None  # input was invalid
            or value <= self.probe_kf40_thickness  # not physically possible
        ):
            self._update_all_labels()
            return

        self.measure_1 = value
        self.recalculate_parameters()

    @Slot()
    def _validate_measure_2(self):
        _txt = self.measure_2_label.text()
        value = self._validate_measure(_txt)

        if (
            value is None  # input was invalid
            or value <= 0  # not physically possible
        ):
            self._update_all_labels()
            return

        self.measure_2 = value
        self.recalculate_parameters()


class LaPDXYZTransformCalculatorApp(BaseCalculatorApp):
    _CALCULATOR_CLASS = LaPDXYZTransformCalculator


if __name__ == "__main__":
    app = LaPDXYZTransformCalculatorApp([])
    app.exec()
