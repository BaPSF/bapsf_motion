"""
Module contains the functionality associated with the
:term:`transformer` configuration overlay portion of the configuration
GUI.
"""
__all__ = ["TransformConfigOverlay"]

import ast
import inspect
import math

from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QComboBox,
)
from typing import Any, Dict, Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.actors import MotionGroup
from bapsf_motion.gui.configure import motion_group_widget as mgw
from bapsf_motion.gui.configure.bases import _ConfigOverlay
from bapsf_motion.gui.configure.helpers import read_parameter_hints
from bapsf_motion.gui.widgets import HLinePlain, QLineEditSpecialized
from bapsf_motion.transform import BaseTransform
from bapsf_motion.transform.helpers import transform_registry, transform_factory
from bapsf_motion.utils import _deepcopy_dict


class TransformConfigOverlay(_ConfigOverlay):
    registry = transform_registry

    def __init__(self, mg: MotionGroup, parent: "mgw.MGWidget" = None):
        super().__init__(mg, parent)

        self._transform = None
        self._params_widget = None  # type: Union[None, QWidget]
        self._transform_inputs = None

        _hints = read_parameter_hints()
        self._parameter_hints = _hints.pop("transform", None)

        # determine starting transform
        if isinstance(self.mg.transform, BaseTransform):
            tr_type = self.mg.transform.transform_type
        elif isinstance(parent, mgw.MGWidget):
            tr_name = parent.transform_dropdown.currentText()
            tr_type = "identity"
            for name, config in parent.transform_defaults:
                if name == tr_name:
                    tr_type = config["type"]
                    self._transform_inputs = _deepcopy_dict(config)
                    break
        else:
            tr_type = "identity"

        # Define BUTTONS
        # Define TEXT WIDGETS
        _txt = QLabel("Select Type:", parent=self)
        _txt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        _font = _txt.font()
        _font.setPointSize(16)
        _txt.setFont(_font)
        self.combo_label = _txt

        # Define ADVANCED WIDGETS
        _w = QComboBox(parent=self)
        _w.setFixedWidth(250)
        _w.addItems(
            list(self.registry.get_names_by_dimensionality(self._mg.drive.naxes))
        )
        _w.setEditable(False)
        _w.setCurrentText(tr_type)
        font = _w.font()
        font.setPointSize(16)
        _w.setFont(font)
        self.combo_widget = _w

        self.setLayout(self._define_layout())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()

        self.combo_widget.currentTextChanged.connect(self._refresh_params_widget)

    def _define_layout(self):

        self._params_widget = self._define_params_widget(
            self.combo_widget.currentText()
        )

        type_layout = QHBoxLayout()
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.addSpacing(8)
        type_layout.addWidget(self.combo_label)
        type_layout.addSpacing(8)
        type_layout.addWidget(self.combo_widget)
        type_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(8)
        layout.addLayout(type_layout)
        layout.addSpacing(24)
        layout.addWidget(self._params_widget)
        layout.addStretch()

        return layout

    def _define_banner_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(
            self.discard_btn,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addStretch()
        layout.addWidget(
            self.done_btn,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        return layout

    @property
    def parameter_hints(self):
        if self._parameter_hints is None:
            self._parameter_hints = dict()

        return self._parameter_hints

    @property
    def transform(self) -> BaseTransform:
        """
        The transform object that been constructed for :attr:`mg`.
        """
        if (
            self._transform is None
            and bool(self.mg.config["transform"])
        ):
            return self.mg.transform

        return self._transform

    @property
    def transform_inputs(self) -> Dict[str, Any]:
        """
        Dictionary of input values for creating the :attr:`transform`
        instance.
        """
        if self._transform_inputs is None:
            self._transform_inputs = {}

        return self._transform_inputs

    @property
    def transform_type(self):
        return self.combo_widget.currentText()

    def _define_params_widget(self, tr_type: str):
        # re-initialized the transform_inputs dictionary
        params = self.registry.get_input_parameters(tr_type)
        _hints = self.parameter_hints.get(tr_type, None)

        if (
            self.transform_inputs is not None
            and "type" in self.transform_inputs
            and tr_type == self.transform_inputs["type"]
        ):
            self._transform_inputs.pop("type")
        elif (
            isinstance(self.transform, BaseTransform)
            and self.transform.transform_type == tr_type
        ):
            self._transform_inputs = {**self.transform.config}
            self._transform_inputs.pop("type")
        else:
            self._transform_inputs = {}

        _widget = QWidget(parent=self)

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(4)

        layout.setColumnMinimumWidth(0, 48)
        layout.setColumnMinimumWidth(2, 8)
        layout.setColumnMinimumWidth(4, 32)
        layout.setColumnMinimumWidth(5, 32)
        layout.setColumnMinimumWidth(6, 48)

        layout.setColumnStretch(0, 0)
        # layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 4)
        layout.setColumnStretch(4, 0)
        layout.setColumnStretch(5, 0)
        layout.setColumnStretch(6, 0)

        ii = 0
        _row_height = 24
        for key, val in params.items():
            # determine the seeded value for the transform input
            if key in self.transform_inputs:
                default = self.transform_inputs[key]
            elif val["param"].default is not val["param"].empty:
                default = val["param"].default
                self.transform_inputs[key] = default
            else:
                default = None
                self.transform_inputs[key] = default

            # determine parameter hing
            _hint = None if (_hints is None or key not in _hints) else _hints[key]

            _txt = QLabel(key, parent=_widget)
            _txt.setFixedHeight(_row_height)
            _txt.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            font = _txt.font()
            font.setPointSize(14)
            _txt.setFont(font)
            _variable_name = _txt

            annotation = val['param'].annotation
            if inspect.isclass(annotation):
                annotation = annotation.__name__
            annotation = f"{annotation}".split(".")[-1]

            _txt = QLabel("", parent=_widget)
            _txt.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter
            )
            _icon = qta.icon("msc.symbol-type-parameter")
            # size = math.floor(0.9 * _row_height)
            size = _row_height
            _txt.setPixmap(_icon.pixmap(QSize(size, size)))
            _txt.setToolTip(annotation)
            _txt.setToolTipDuration(30000)
            _type_icon = _txt

            text = "" if default is None else f"{default}"
            _txt = QLineEditSpecialized(text, parent=_widget)
            _txt.setObjectName(key)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            _txt.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            font = _txt.font()
            font.setPointSize(14)
            _txt.setFont(font)
            _input = _txt
            if _hint is not None:
                _input.setPlaceholderText(_hint)
            _input.editingFinishedPayload.connect(self._update_transform_inputs)

            _txt = QLabel("", parent=_widget)
            _txt.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter
            )
            _icon = qta.icon("fa.question-circle-o")
            size = math.floor(0.95 * _row_height)
            _txt.setPixmap(_icon.pixmap(QSize(size, size)))
            _txt.setToolTip("\n".join(val["desc"]))
            _txt.setToolTipDuration(30000)
            _help_icon = _txt

            layout.setRowMinimumHeight(ii, _row_height)
            layout.setRowStretch(ii, 0)

            layout.addWidget(_variable_name, ii, 1)
            layout.addWidget(_input, ii, 3)
            layout.addWidget(_type_icon, ii, 4)
            layout.addWidget(_help_icon, ii, 5)

            ii += 1

        _widget.setLayout(layout)
        return _widget

    @Slot(str)
    def _refresh_params_widget(self, tr_type):
        _widget = self._define_params_widget(tr_type)

        old_widget = self._params_widget
        self.layout().replaceWidget(old_widget, _widget)
        self._params_widget = _widget

        old_widget.close()
        old_widget.deleteLater()

        self._validate_inputs()

    @Slot(object)
    def _update_transform_inputs(self, input_widget: "QLineEditSpecialized"):
        param = input_widget.objectName()
        _input_string = input_widget.text()

        try:
            _input = ast.literal_eval(_input_string)
        except (ValueError, SyntaxError):
            params = self.registry.get_input_parameters(self.transform_type)
            _type = params[param]["param"].annotation
            if inspect.isclass(_type) and issubclass(_type, str):
                _input = _input_string
            elif _input_string == "":
                _input = None
            else:
                self.logger.exception(
                    f"Input '{input_widget.text()}' is not a valid type for '{param}'."
                )
                _input = None
                input_widget.setText("")
                raise

        self.transform_inputs[param] = _input

        self.logger.info(
            f"Updating input parameter {param} to {_input} for transformation "
            f"type {self.transform_type}."
        )

        self._validate_inputs()

    def _validate_inputs(self):
        tr_type = self.transform_type
        _inputs = self.transform_inputs
        params = self.registry.get_input_parameters(tr_type)

        for key, val in _inputs.items():
            annotation = params[key]["param"]

            if val is not None:
                continue
            elif (
                annotation is None
                or (
                    hasattr(annotation, "__args__")
                    and type(None) in annotation.__args__
                )
            ):
                # val is None and is allowed to be None
                continue
            else:
                # not all inputs have been defined yet
                self.change_validation_state(False)
                return

        try:
            transform = transform_factory(
                self.mg.drive, tr_type=self.transform_type, **self.transform_inputs
            )
            self._transform = transform
            self.change_validation_state(True)
        except (ValueError, TypeError):
            self.logger.exception("Supplied transform input arguments are not valid.")
            self.change_validation_state(False)
            raise

    def change_validation_state(self, valid: bool = False):
        self.done_btn.setEnabled(valid)

    def return_and_close(self):
        config = self.transform.config

        self.logger.info(
            f"New transform configuration of type {config['type']} is "
            f"being returned."
        )
        self.returnConfig.emit(config)
        self.close()
