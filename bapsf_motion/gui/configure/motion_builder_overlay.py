__all__ = ["MotionBuilderConfigOverlay"]

import ast
import inspect
import numpy as np
import matplotlib as mpl
import re

from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QDoubleValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QWidget,
    QSizePolicy,
    QListWidget,
    QVBoxLayout,
    QComboBox,
)
from typing import Any, Dict, Optional, Union

# noqa
# import of qtawesome must happen after the PySide6 imports
import qtawesome as qta

from bapsf_motion.actors import MotionGroup
from bapsf_motion.gui.configure import motion_group_widget as mgw
from bapsf_motion.gui.configure.bases import _ConfigOverlay
from bapsf_motion.gui.widgets import (
    HLinePlain,
    QLineEditSpecialized,
    StyleButton,
    VLinePlain,
)
from bapsf_motion.motion_builder import MotionBuilder
from bapsf_motion.motion_builder.layers import layer_registry
from bapsf_motion.motion_builder.exclusions import exclusion_registry, GovernExclusion
from bapsf_motion.utils import _deepcopy_dict
from bapsf_motion.utils import units as u

# noqa
mpl.use("qtagg")  # matplotlib's backend for Qt bindings
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa


class MotionBuilderConfigOverlay(_ConfigOverlay):
    layer_registry = layer_registry
    exclusion_registry = exclusion_registry

    def __init__(self, mg: MotionGroup, parent: "mgw.MGWidget" = None):
        super().__init__(mg, parent)

        self._mb = None

        self._space_input_widgets = {}  # type: Dict[str, Dict[str, QLineEditSpecialized]]

        # _param_inputs:
        #     dictionary of input parameters for instantiating an exclusion or
        #     points layer
        # _params_widget:
        #     top enclosing widget for setting and configuring parameter inputs
        #     for an exclusion or point layer
        # _params_field_widget:
        #     child widget of _params_widget that contains the actual inpu fields
        #     for configuring _param_inputs
        # _params_input_widgets:
        #     dictionary of the actual widgets that control the _param_inputs
        #     values
        self._param_inputs = {}  # type: Dict[str, Any]
        self._params_widget = None  # type: Union[QWidget, None]
        self._params_field_widget = None  # type: Union[QWidget, None]
        self._params_input_widgets = {}  # type: Dict[str, Dict[str, QLineEditSpecialized]]

        # Define BUTTONS

        self.add_ly_btn = self._generate_btn_widget("ADD")
        self.remove_ly_btn = self._generate_btn_widget("REMOVE")
        self.remove_ly_btn.setEnabled(False)
        self.edit_ly_btn = self._generate_btn_widget("EDIT")
        self.edit_ly_btn.setEnabled(False)

        self.add_ex_btn = self._generate_btn_widget("ADD")
        self.remove_ex_btn = self._generate_btn_widget("REMOVE")
        self.remove_ex_btn.setEnabled(False)
        self.edit_ex_btn = self._generate_btn_widget("EDIT")
        self.edit_ex_btn.setEnabled(False)

        self.params_add_btn = self._generate_btn_widget("Add / Update")
        self.params_discard_btn = self._generate_btn_widget("Discard")

        # Define TEXT WIDGETS
        _txt = QComboBox(parent=self)
        _txt.setMinimumWidth(200)
        _txt.setMaximumWidth(400)
        _txt.setEditable(False)
        # _txt.addItems(_available)
        # _txt.setCurrentText(_type)
        self.params_combo_box = _txt

        _txt = QLabel("", parent=self)
        self.params_label = _txt

        # Define ADVANCED WIDGETS

        self.layer_list_box = QListWidget(parent=self)
        self.layer_list_box.setMinimumHeight(250)
        self.exclusion_list_box = QListWidget(parent=self)
        self.exclusion_list_box.setMinimumHeight(250)

        self.mpl_canvas = FigureCanvas()
        self.mpl_canvas.setParent(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._initialize_motion_builder()
        self.setLayout(self._define_layout())

        self.update_exclusion_list_box()
        self.update_layer_list_box()
        self.update_canvas()

        self._connect_signals()

    def _connect_signals(self):
        super()._connect_signals()

        self.configChanged.connect(self._config_changed_handler)

        self.add_ex_btn.clicked.connect(self._exclusion_configure_new)
        self.remove_ex_btn.clicked.connect(self._exclusion_remove_from_mb)
        self.edit_ex_btn.clicked.connect(self._exclusion_modify_existing)

        self.add_ly_btn.clicked.connect(self._layer_configure_new)
        self.remove_ly_btn.clicked.connect(self._layer_remove_from_mb)
        self.edit_ly_btn.clicked.connect(self._layer_modify_existing)

        self.params_discard_btn.clicked.connect(self._hide_and_clear_params_widget)
        self.params_add_btn.clicked.connect(self._add_to_mb)

        self.params_combo_box.currentTextChanged.connect(
            self._refresh_params_widget_from_combo_box_change
        )

        self.layer_list_box.itemSelectionChanged.connect(
            self.layer_list_box_set_btn_enable
        )
        self.exclusion_list_box.itemSelectionChanged.connect(
            self.exclusion_list_box_set_btn_enable
        )

    def _define_layout(self):
        #
        #  +-------------------------------------------------------+
        #  | banner_layout                                         |
        #  +-------------------+-----------------------------------+
        #  |     sidebar       | right_area                        |
        #  |                   |                                   |
        #  | +--------------+  |  +-----------------------------+  |
        #  | | motion_space |  |  | Plot                        |  |
        #  | |              |  |  |                             |  |
        #  | +--------------+  |  |                             |  |
        #  |                   |  |                             |  |
        #  | +--------------+  |  +-----------------------------+  |
        #  | |  exclusion   |  |                                   |
        #  | |  list        |  |  +--params_widget--------------+  |
        #  | +--------------+  |  |                             |  |
        #  |                   |  | banner                      |  |
        #  | +--------------+  |  |                             |  |
        #  | |  layer       |  |  | +--params_field_widget----+ |  |
        #  | |  list        |  |  | |                         | |  |
        #  | +--------------+  |  | +-------------------------+ |  |
        #  |                   |  +-----------------------------+  |
        #  +-------------------+-----------------------------------+
        #
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(0)
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.addWidget(self._define_sidebar_widget())
        sub_layout.addSpacing(8)
        sub_layout.addWidget(VLinePlain(parent=self))
        sub_layout.addWidget(self._define_right_area_widget())

        layout = QVBoxLayout()
        layout.setSpacing(12)

        layout.addLayout(self._define_banner_layout())
        layout.addWidget(HLinePlain(parent=self))
        layout.addSpacing(6)
        layout.addLayout(sub_layout)

        return layout

    @property
    def dimensionality(self):
        return self.mg.drive.naxes

    @property
    def axis_names(self):
        return self.mg.drive.anames

    @property
    def mb(self) -> Union[MotionBuilder, None]:
        if (
            self._mb is None
            and isinstance(self.mg, MotionGroup)
            and isinstance(self.mg.mb, MotionBuilder)
        ):
            return self.mg.mb

        return self._mb

    # -- LAYOUT AND WIDGET DEFINITIONS --

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

    def _define_sidebar_widget(self):
        _widget = QWidget(parent=self)
        _widget.setMinimumWidth(350)
        _widget.setMaximumWidth(500)
        _widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        layout.addLayout(self._define_motion_space_layout())
        layout.addSpacing(20)
        layout.addLayout(self._define_exclusion_list_layout())
        layout.addSpacing(24)
        layout.addLayout(self._define_layer_list_layout())
        layout.addStretch()

        return _widget

    def _define_right_area_widget(self):
        _widget = QWidget(parent=self)
        _widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(_widget)
        layout.addWidget(self.mpl_canvas)
        layout.addWidget(HLinePlain(parent=self))
        layout.addWidget(self._define_params_widget())

        return _widget

    def _define_motion_space_layout(self):

        _txt = QLabel("Motion Space", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)

        layout = QGridLayout()
        layout.setContentsMargins(8, 4, 12, 4)
        layout.setSpacing(4)
        layout.setColumnMinimumWidth(4, 18)
        layout.setRowMinimumHeight(1, 12)
        layout.addWidget(
            _txt, 0, 0, 1, 8,
            alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
        )

        for ii, args in self.mb.config["space"].items():
            axis = self.mg.drive.axes[ii]
            name = args["label"]

            _txt = QLabel(name, parent=self)
            font = _txt.font()
            font.setPointSize(12)
            _txt.setFont(font)
            axis_label = _txt

            _txt = QLabel("range", parent=self)
            _txt.setFont(font)
            range_label = _txt

            _txt = QLineEditSpecialized(f"{args['range'][0]:.2f}", parent=self)
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_min")
            _txt.setValidator(QDoubleValidator(decimals=1))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            min_range = _txt

            _txt = QLineEditSpecialized(f"{args['range'][1]:.2f}", parent=self)
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_max")
            _txt.setValidator(QDoubleValidator(decimals=1))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            max_range = _txt

            _txt = QLabel("Δ", parent=self)
            _txt.setFont(font)
            delta_label = _txt

            _txt = QLineEditSpecialized(
                f"{(args['range'][1] - args['range'][0]) / args['num']:.2f}",
                parent=self
            )
            _txt.setFont(font)
            _txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            _txt.setObjectName(f"{name}_delta")
            _txt.setValidator(QDoubleValidator(decimals=2))
            _txt.editingFinishedPayload.connect(self._validate_space_inputs)
            delta = _txt

            _txt = QLabel(f"{axis.units}", parent=self)
            _txt.setFont(font)
            unit_label = _txt

            layout.addWidget(
                axis_label, ii + 2, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            layout.addWidget(
                range_label, ii + 2, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                min_range, ii + 2, 2, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                max_range, ii + 2, 3, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                delta_label, ii + 2, 5, 1, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            layout.addWidget(
                delta, ii + 2, 6, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter
            )
            layout.addWidget(
                unit_label, ii + 2, 7, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft
            )

            self._space_input_widgets[name] = {
                "min": min_range,
                "max": max_range,
                "delta": delta,
            }

        return layout

    def _define_exclusion_list_layout(self):

        _txt = QLabel("Exclusion Layers", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)
        title = _txt

        ex_types = set(ex.exclusion_type for ex in self.mb.exclusions)

        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        ex_names = []
        if not _available:
            self.logger.warning(
                "There are no coded exclusion layers that work with the "
                f"dimensionality of the existing probe drive, {self.dimensionality}."
            )
            self.add_ex_btn.setEnabled(False)
            self.remove_ex_btn.setEnabled(False)
            self.edit_ex_btn.setEnabled(False)

            exclusions = self.mb.exclusions.copy()
            for ex in exclusions:
                self.mb.remove_exclusion(ex.name)

        elif ex_types - _available:
            exclusions = self.mb.exclusions.copy()
            for ex in exclusions:
                if ex.exclusion_type in _available:
                    ex_names.append(
                        self._generate_list_name(ex.name, ex.exclusion_type)
                    )
                    continue

                self.mb.remove_exclusion(ex.name)

        self.exclusion_list_box.addItems(ex_names)

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(8)
        sub_layout.addWidget(self.add_ex_btn)
        sub_layout.addWidget(self.remove_ex_btn)
        sub_layout.addWidget(self.edit_ex_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            title,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addSpacing(2)
        layout.addWidget(self.exclusion_list_box)
        layout.addLayout(sub_layout)

        return layout

    def _define_layer_list_layout(self):

        _txt = QLabel("Point Layers", parent=self)
        font = _txt.font()
        font.setPointSize(16)
        font.setBold(True)
        _txt.setFont(font)
        title = _txt

        ly_types = set(ly.layer_type for ly in self.mb.layers)

        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        ly_names = []
        if not _available:
            self.logger.warning(
                "There are no coded point layers that work with the "
                f"dimensionality of the existing probe drive, {self.dimensionality}."
            )
            self.add_ly_btn.setEnabled(False)
            self.remove_ly_btn.setEnabled(False)
            self.edit_ly_btn.setEnabled(False)

            layers = self.mb.layers.copy()
            for ly in layers:
                self.mb.remove_layer(ly.name)

        elif ly_types - _available:
            layers = self.mb.layers.copy()
            for ly in layers:
                if ly.layer_type in _available:
                    ly_names.append(
                        self._generate_list_name(ly.name, ly.layer_type)
                    )
                    continue

                self.mb.remove_layer(ly.name)

        self.layer_list_box.addItems(ly_names)

        sub_layout = QHBoxLayout()
        sub_layout.setContentsMargins(0, 0, 0, 0)
        sub_layout.setSpacing(8)
        sub_layout.addWidget(self.add_ly_btn)
        sub_layout.addWidget(self.remove_ly_btn)
        sub_layout.addWidget(self.edit_ly_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            title,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addSpacing(2)
        layout.addWidget(self.layer_list_box)
        layout.addLayout(sub_layout)

        return layout

    def _define_plot_layout(self):
        ...

    def _define_params_widget(self):
        _widget = QWidget(parent=self)
        _widget.setMinimumHeight(300)
        size_policy = _widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        _widget.setSizePolicy(size_policy)
        layout = QVBoxLayout(_widget)

        self.params_add_btn.setEnabled(False)

        hline = HLinePlain(parent=self)
        hline.set_color(30, 30, 30)
        hline.setLineWidth(2)

        self._params_field_widget = QWidget(parent=_widget)

        banner_layout = QHBoxLayout()
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.setSpacing(8)

        banner_layout.addWidget(
            self.params_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        banner_layout.addSpacing(20)
        banner_layout.addWidget(
            self.params_combo_box,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        banner_layout.addStretch()
        banner_layout.addWidget(
            self.params_discard_btn,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        banner_layout.addWidget(
            self.params_add_btn,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )

        layout.addLayout(banner_layout)
        layout.addWidget(hline)
        layout.addWidget(self._params_field_widget)
        layout.addStretch()

        self._params_widget = _widget
        self._params_widget.hide()
        return self._params_widget

    def _define_params_field_widget(self, ex_or_ly, _type):
        _registry = (
            self.exclusion_registry
            if ex_or_ly == "exclusion"
            else self.layer_registry
        )

        self._param_inputs.update(
            {"_type": _type, "_registry": _registry}
        )

        params = _registry.get_input_parameters(_type)

        _widget = QWidget(parent=self._params_widget)
        layout = QGridLayout(_widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # layout.setColumnStretch(0, 2)
        # layout.setColumnStretch(1, 2)
        # layout.setColumnStretch(2, 4)
        # layout.setColumnStretch(3, 1)
        # layout.setColumnStretch(4, 1)

        ii = 0
        for key, val in params.items():
            # determine the seeded value for the transform input
            if key in self._param_inputs:
                default = self._param_inputs[key]
            elif val["param"].default is not val["param"].empty:
                default = val["param"].default
                self._param_inputs[key] = default
            else:
                default = None
                self._param_inputs[key] = default

            _txt = QLabel(key, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _label = _txt

            annotation = val['param'].annotation
            if inspect.isclass(annotation):
                annotation = annotation.__name__
            annotation = f"{annotation}".split(".")[-1]

            _txt = QLabel(annotation, parent=_widget)
            font = _txt.font()
            font.setPointSize(16)
            font.setBold(True)
            _txt.setFont(font)
            _type = _txt

            text = "" if default is None else f"{default}"
            _txt = QLineEditSpecialized(text, parent=_widget)
            _txt.setObjectName(key)
            _txt.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            font = _txt.font()
            font.setPointSize(16)
            _txt.setFont(font)
            _input = _txt
            _input.editingFinishedPayload.connect(self._update_param_inputs)

            _txt = QLabel("", parent=_widget)
            _icon = qta.icon("fa.question-circle-o").pixmap(QSize(16, 16))  # type: QIcon
            _txt.setPixmap(_icon)
            _txt.setToolTip("\n".join(val["desc"]))
            _txt.setToolTipDuration(10000)
            _txt.setMaximumWidth(24)
            _help = _txt

            layout.addWidget(_label, ii, 0, alignment=Qt.AlignmentFlag.AlignRight)
            layout.addWidget(_type, ii, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(_input, ii, 2, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(_help, ii, 3, alignment=Qt.AlignmentFlag.AlignLeft)
            ii += 1

        return _widget

    # -- WIDGET INTERACTION FUNCTIONALITY --

    def _config_changed_handler(self):
        # Note: none of the methods executed here should cause a
        #       configChanged event
        self._validate_mb()

        # now update displays
        self.update_exclusion_list_box()
        self.update_layer_list_box()
        self.update_canvas()

    def _exclusion_configure_new(self):
        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText("New Exclusion")

        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        if self.mb.exclusions and isinstance(self.mb.exclusions[0], GovernExclusion):
            # remove govern exclusion since we can only have one defined
            for name in tuple(_available):
                ex = self.exclusion_registry.get_exclusion(name)
                if issubclass(ex, GovernExclusion):
                    _available.remove(name)

        self._refresh_params_combo_box(_available)
        self.params_combo_box.setObjectName("exclusion")

        self._refresh_params_widget()
        self._show_params_widget()

    def _exclusion_modify_existing(self):
        item = self.exclusion_list_box.currentItem()
        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        ex = None
        for _ex in self.mb.exclusions:
            if _ex.name == name:
                ex = _ex
                break
        if ex is None:
            return

        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText(ex.name)
        _available = self.exclusion_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available, ex.exclusion_type)
        self.params_combo_box.setObjectName("exclusion")

        self._param_inputs = ex.config.copy()
        self._param_inputs.pop("type")

        self._refresh_params_widget()
        self._show_params_widget()

    def _exclusion_remove_from_mb(self):
        ex_row = self.exclusion_list_box.currentRow()
        ex = self.exclusion_list_box.takeItem(ex_row)

        name = self._get_layer_name_from_list_name(ex.text())
        if name is None:
            return

        self.mb.remove_exclusion(name)
        # ex.deleteLater()

        # TODO: remove params_widget if the removed exclusion is currently
        #       populating the params_widget

        self.configChanged.emit()

    def _hide_and_clear_params_widget(self):
        self._params_field_widget.setEnabled(False)
        self._params_widget.hide()
        self._param_inputs = {}

    def _layer_configure_new(self):
        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText("New Layer")

        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available)
        self.params_combo_box.setObjectName("layer")

        self._refresh_params_widget()
        self._show_params_widget()

    def _layer_modify_existing(self):
        item = self.layer_list_box.currentItem()
        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        ly = None
        for _ly in self.mb.layers:
            if _ly.name == name:
                ly = _ly
                break
        if ly is None:
            return

        if not self._params_widget.isHidden():
            self._hide_and_clear_params_widget()

        self.params_label.setText(ly.name)
        _available = self.layer_registry.get_names_by_dimensionality(
            self.dimensionality
        )
        self._refresh_params_combo_box(_available, ly.layer_type)
        self.params_combo_box.setObjectName("layer")

        self._param_inputs = ly.config.copy()
        self._param_inputs.pop("type")

        self._refresh_params_widget()
        self._show_params_widget()

    def _layer_remove_from_mb(self):
        ly_row = self.layer_list_box.currentRow()
        item = self.layer_list_box.takeItem(ly_row)

        name = self._get_layer_name_from_list_name(item.text())
        if name is None:
            return

        self.logger.info(f"Removing layer {name}.")
        self.mb.remove_layer(name)
        # ex.deleteLater()

        # TODO: remove params_widget if the removed exclusion is currently
        #       populating the params_widget

        self.configChanged.emit()

    def _refresh_params_combo_box(self, items, current: Optional[str] = None):
        self.params_combo_box.currentTextChanged.disconnect()

        self.params_combo_box.setObjectName("")
        self.params_combo_box.clear()
        self.params_combo_box.addItems(items)
        if current is None:
            self.params_combo_box.setCurrentIndex(0)
        else:
            self.params_combo_box.setCurrentText(current)

        self.params_combo_box.currentTextChanged.connect(
            self._refresh_params_widget_from_combo_box_change
        )

    def _refresh_params_widget(self):
        self.params_add_btn.setEnabled(False)

        _type = self.params_combo_box.currentText()
        ex_or_ly = self.params_combo_box.objectName()

        _widget = self._define_params_field_widget(ex_or_ly, _type)

        old_widget = self._params_field_widget
        self._params_widget.layout().replaceWidget(old_widget, _widget)
        self._params_field_widget = _widget

        old_widget.close()
        old_widget.deleteLater()

        self._validate_inputs()

    def _refresh_params_widget_from_combo_box_change(self):
        self._param_inputs = {}
        self._refresh_params_widget()

    def _show_params_widget(self):
        self._params_field_widget.setEnabled(True)
        self._params_widget.show()

    @Slot(object)
    def _update_param_inputs(self, input_widget: "QLineEditSpecialized"):
        param = input_widget.objectName()
        _input_string = input_widget.text()

        _type = self._param_inputs["_type"]
        _registry = self._param_inputs["_registry"]

        try:
            _input = ast.literal_eval(_input_string)
        except (ValueError, SyntaxError):
            params = _registry.get_input_parameters(_type)
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

        self._param_inputs[param] = _input

        self.logger.info(
            f"Updating input parameter {param} to {_input} for transformation "
            f"type {_type}."
        )

        self._validate_inputs()

    @Slot(object)
    def _validate_space_inputs(self, input_widget: QLineEditSpecialized):
        self.logger.info("Validating space inputs")
        w_name = input_widget.objectName()
        match = re.compile(r"(?P<label>.+)_(?P<what>(min|max|delta))").fullmatch(w_name)
        if match is None:
            # input_widget does not have a name corresponding to the space inputs
            return

        axis_index = None
        axis_config = None
        axis_label = match.group("label")
        axis_input_type = match.group("what")

        space_config = self.mb.config["space"].copy()
        for key, value in space_config.items():
            if value["label"] == axis_label:
                axis_index = key
                axis_config = value
                break

        if axis_config is None:
            # This should never happen
            return None

        if axis_input_type == "delta":
            old_val = (
                    (axis_config["range"][1] - axis_config["range"][0])
                    / axis_config["num"]
            )
        else:
            old_val = (
                axis_config["range"][0]
                if axis_input_type == "min"
                else axis_config["range"][0]
            )

        try:
            new_val = float(input_widget.text())
            new_val_good = True
        except ValueError:
            new_val = None
            new_val_good = False

        range_window = axis_config["range"][1] - axis_config["range"][0]
        old_delta = range_window / axis_config["num"]

        if not new_val_good:
            pass
        elif axis_input_type == "min" and new_val >= axis_config["range"][1]:
            new_val_good = False
        elif axis_input_type == "min" and (
                old_delta / (axis_config["range"][1] - new_val) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "min":
            axis_config["range"][0] = new_val
            axis_config["num"] = int(
                np.ceil(
                    (axis_config["range"][1] - new_val) / old_delta
                )
            )
        elif axis_input_type == "max" and new_val <= axis_config["range"][0]:
            new_val_good = False
        elif axis_input_type == "max" and (
                old_delta / (new_val - axis_config["range"][0]) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "max":
            axis_config["range"][1] = new_val
            axis_config["num"] = int(
                np.ceil(
                    (new_val - axis_config["range"][0]) / old_delta
                )
            )
        elif axis_input_type == "delta" and (
                new_val / (axis_config["range"][1] - axis_config["range"][0]) >= 0.1
        ):
            new_val_good = False
        elif axis_input_type == "delta":
            num = int(
                np.ceil(
                    (axis_config["range"][1] - axis_config["range"][0]) / new_val
                )
            )
            axis_config["num"] = num

        if not new_val_good:
            input_widget.setText(f"{old_val:.3f}")
            return

        space_config[axis_index] = axis_config
        config = {
            "space": space_config,
            "exclusion": self.mb.config.get("exclusion", None),
            "layer": self.mb.config.get("layer", None),
        }
        self._spawn_motion_builder(config)

    def _validate_inputs(self):
        self.logger.info("Validating motion layer parameter inputs")
        _inputs = self._param_inputs.copy()
        _type = _inputs.pop("_type")
        _registry = _inputs.pop("_registry")
        params = _registry.get_input_parameters(_type)

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
            _layer = _registry.factory(
                self.mb._ds,
                _type=_type,
                skip_ds_add=True,
                **_inputs,
            )
            # self._transform = transform
            self.change_validation_state(True)
        except (ValueError, TypeError):
            self.logger.exception("Supplied input arguments are not valid.")
            self.change_validation_state(False)
            raise

    def change_validation_state(self, valid: bool = False):
        self.params_add_btn.setEnabled(valid)

    def exclusion_list_box_set_btn_enable(self, enable=True):
        self.edit_ex_btn.setEnabled(enable)
        self.remove_ex_btn.setEnabled(enable)

    def layer_list_box_set_btn_enable(self, enable=True):
        self.edit_ly_btn.setEnabled(enable)
        self.remove_ly_btn.setEnabled(enable)

    def update_canvas(self):
        self.logger.info("Redrawing plot...")
        self.logger.info(f"MB config = {self.mb.config}")

        self.mpl_canvas.figure.clear()
        ax = self.mpl_canvas.figure.gca()
        xdim, ydim = self.mb.mspace_dims
        self.mb.mask.plot(x=xdim, y=ydim, ax=ax)

        pts = self.mb.motion_list
        if pts is not None:
            ax.scatter(
                x=pts[..., 0],
                y=pts[..., 1],
                linewidth=1,
                s=2 ** 2,
                facecolors="deepskyblue",
                edgecolors="black",
            )

        self.mpl_canvas.draw()

    def update_exclusion_list_box(self):
        self.logger.info("Updating Exclusion List Box")
        self.remove_ex_btn.setEnabled(False)
        self.edit_ex_btn.setEnabled(False)

        ex_names = set(
            self._generate_list_name(ex.name, ex.exclusion_type)
            for ex in self.mb.exclusions
        )
        self.exclusion_list_box.clear()

        if not ex_names:
            return

        self.exclusion_list_box.addItems(ex_names)

    def update_layer_list_box(self):
        self.logger.info("Updating Layer List Box")
        self.remove_ly_btn.setEnabled(False)
        self.edit_ly_btn.setEnabled(False)

        ly_names = set(
            self._generate_list_name(ly.name, ly.layer_type)
            for ly in self.mb.layers
        )

        self.layer_list_box.clear()

        if not ly_names:
            return

        self.layer_list_box.addItems(ly_names)

    # -- NORMAL METHODS --

    def _add_to_mb(self):
        _inputs = self._param_inputs.copy()
        _type = _inputs.pop("_type")
        _registry = _inputs.pop("_registry")
        _name = self.params_label.text()

        if _registry is self.exclusion_registry and _name == "New Exclusion":
            self.mb.add_exclusion(_type, **_inputs)
        elif _registry is self.exclusion_registry:
            # modifying existing exclusion
            self.mb.remove_exclusion(_name)
            self.mb.add_exclusion(_type, **_inputs)
        elif _name == "New Layer":
            self.mb.add_layer(_type, **_inputs)
        else:
            self.mb.remove_layer(_name)
            self.mb.add_layer(_type, **_inputs)

        self._hide_and_clear_params_widget()
        self.configChanged.emit()

    def _generate_btn_widget(self, txt: str):
        btn = StyleButton(txt, parent=self)
        btn.setFixedHeight(32)
        font = btn.font()
        font.setPointSize(16)
        btn.setFont(font)
        btn.setEnabled(True)

        return btn

    @staticmethod
    def _generate_list_name(name, _type):
        return f"{name:<17} <type = {_type}>"

    @staticmethod
    def _get_layer_name_from_list_name(list_name):
        match = re.compile(
            r"(?P<name>\S+)\s+(<type = )(?P<type>\S+)(>)"
        ).fullmatch(list_name)
        return None if match is None else match.group("name")

    def _initialize_motion_builder(self):
        if (
            not isinstance(self.mg, MotionGroup)
            or not isinstance(self.mb, MotionBuilder)
            or not isinstance(self.mg.mb, MotionBuilder)
        ):
            pass
        elif self.mb is self.mg.mb:
            config = _deepcopy_dict(self.mb.config)
            self._spawn_motion_builder(config)
            return

        config = {"space": {}}
        for ii, aname in enumerate(self.axis_names):
            axis = self.mg.drive.axes[ii]

            if axis.units.physical_type == u.get_physical_type("length"):
                _range = [-55.0, 55.0]
                num = int(np.ceil((_range[1] - _range[0]) / .25))

                _convert = (1 * u.cm).to(axis.units)  # type: u.Quantity
                _convert = _convert.value
                _range = [float(r * _convert) for r in _range]
            elif axis.units.physical_type == u.get_physical_type("angle"):
                _x = 3 * 360.0
                delta = 5.0
                if axis.units == u.rad:
                    _x = _x * (2.0 * np.pi / 360.0)
                    delta = delta * (np.pi / 180.0)

                _range = [float(-_x), float(_x)]
                num = int(np.ceil(2.0 * _x / delta))
            else:  # this should not happen
                _range = [-1.0, 1.0]
                num = 11

            config["space"][ii] = {
                "label": aname,
                "range": _range,
                "num": num,
            }

        self._spawn_motion_builder(config)

    def _spawn_motion_builder(self, config):
        self.logger.info("Rebuilding motion builder...")
        space = list(config["space"].values())

        exclusions = config.get("exclusion", None)
        if exclusions is not None:
            exclusions = list(exclusions.values())

        layers = config.get("layer", None)
        if layers is not None:
            layers = list(layers.values())

        self.logger.info(f"space looks like : {space}")
        self.logger.info(f"exclusion look like : {exclusions}")
        self.logger.info(f"layer looks like : {layers}")

        self._mb = MotionBuilder(space=space, exclusions=exclusions, layers=layers)
        self.configChanged.emit()
        return self._mb

    def _validate_mb(self):
        if not isinstance(self.mb, MotionBuilder):
            self.done_btn.setEnabled(False)
            return
        elif len(self.mb.layers) == 0:
            self.done_btn.setEnabled(False)
            return

        self.done_btn.setEnabled(True)

    def return_and_close(self):
        config = self.mb.config

        self.logger.info(
            f"New MotionBuilder configuration is being returned, {config}."
        )
        self.returnConfig.emit(config)
        self.close()
