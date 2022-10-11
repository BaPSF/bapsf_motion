__all__ = ["BaseLayer"]

import re
import xarray as xr

from abc import ABC, abstractmethod


class BaseLayer(ABC):
    base_name = "point_layer"
    name_pattern = re.compile(r"point_layer(?P<number>[0-9]+)")

    def __init__(self, ds: xr.Dataset, **kwargs):
        self.inputs = kwargs

        self._ds = self._validate_ds(ds)
        self.name = self._determine_name()
        self._validate_inputs()

        # assign all, and only, instance variables above the super
        # - definition of instance variables is mandatory, otherwise
        #   self._generate_points will not operate correctly
        points = self._generate_point_matrix()
        dims = [f"{self.name}_d{ii}" for ii in range(points.ndim - 1)]
        dims.append("space")
        self._ds[self.name] = xr.DataArray(
            data=points,
            dims=dims,
        )

    def _determine_name(self):
        if hasattr(self, "name"):
            return self.name

        names = set(self._ds.data_vars.keys())
        n_existing_layers = 0
        for name in names:
            if self.name_pattern.fullmatch(name) is not None:
                n_existing_layers += 1

        return f"{self.base_name}{n_existing_layers + 1:d}"

    @staticmethod
    def _validate_ds(ds: xr.Dataset):
        if not isinstance(ds, xr.Dataset):
            raise TypeError(
                f"Expected type xarray.Dataset for argument "
                f"'ds', got type {type(ds)}."
            )

        if "mask" not in ds.data_vars:
            raise ValueError(
                f"The xarray.DataArray 'mask' representing the "
                "boolean mask of the motion space has not been "
                "defined."
            )

        return ds

    @property
    def points(self):
        return self._ds[self.name]

    @property
    def mspace_coords(self):
        return self._ds.mask.coords

    @property
    def mspace_dims(self):
        return self._ds.mask.dims

    @property
    def mspace_ndims(self):
        return len(self.mspace_dims)

    @abstractmethod
    def _generate_point_matrix(self):
        ...

    @abstractmethod
    def _validate_inputs(self):
        ...
