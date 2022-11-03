__all__ = ["BaseLayer"]

import re
import numpy as np
import xarray as xr

from abc import ABC, abstractmethod
from typing import List

from bapsf_motion.motion_list.item import MLItem


class BaseLayer(ABC, MLItem):
    _layer_type = NotImplemented  # type: str

    def __init__(self, ds: xr.Dataset, *, skip_ds_add=False, **kwargs):
        self._config_keys = {"type"}.union(set(kwargs.keys()))
        self.inputs = kwargs
        self.skip_ds_add = skip_ds_add
        self.composed_layers = []  # type: List[BaseLayer]

        super().__init__(
            ds=ds,
            base_name="point_layer",
            name_pattern=re.compile(r"point_layer(?P<number>[0-9]+)"),
        )

        self._validate_inputs()

        if self.skip_ds_add:
            return

        # store points in the Dataset
        self.regenerate_point_matrix()

    @property
    def layer_type(self):
        return self._layer_type

    @property
    def points(self):
        try:
            return self.item
        except KeyError:
            return self._generate_point_matrix_da()

    @property
    def config(self):
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.layer_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

    @abstractmethod
    def _generate_point_matrix(self):
        ...

    @abstractmethod
    def _validate_inputs(self):
        ...

    def _generate_point_matrix_da(self):
        # _generate_point_matrix() does not return a DataArray, then
        # convert it to one.
        points = self._generate_point_matrix()

        if isinstance(points, xr.DataArray):
            return points

        if self.name in self._ds.data_vars:
            dims = self._ds[self.name].dims
        else:
            dims = [f"{self.name}_d{ii}" for ii in range(points.ndim - 1)]
            dims.append("space")

        return xr.DataArray(data=points, dims=dims)

    def regenerate_point_matrix(self):
        self._ds[self.name] = self._generate_point_matrix_da()
