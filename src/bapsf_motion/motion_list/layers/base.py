"""Module that defines the `BaseLayer` abstract class."""
__all__ = ["BaseLayer"]

import re
import numpy as np
import xarray as xr

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

from bapsf_motion.motion_list.item import MLItem


class BaseLayer(ABC, MLItem):
    """
    Abstract base class for :term:`motion layer` classes.

    Parameters
    ----------
    ds: `~xr.Dataset`
        The `xarray` `~xarray.Dataset` the motion list configuration
        is constructed in.

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the motion points and skip adding it to the
        `~xarray.Dataset`. (DEFAULT: `False`)

    kwargs:
        Keyword arguments that are specific to the subclass.
    """

    # TODO: Can we define a __del__ that properly removes a layer and
    #       its dependencies from the motion list dataset?

    _layer_type = NotImplemented  # type: str

    def __init__(
        self, ds: xr.Dataset, *, skip_ds_add: bool = False, **kwargs
    ):
        self._config_keys = {"type"}.union(set(kwargs.keys()))
        self._inputs = kwargs
        self.skip_ds_add = skip_ds_add

        self.composed_layers = []  # type: List[BaseLayer]
        """
        List of dependent :term:`motion layers` used to make this
        more complex :term:`motion layer`.
        """

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
    def layer_type(self) -> str:
        """
        String naming the :term:`motion layer` type.  This is unique
        among all subclasses of `BaseLayer`.
        """
        # TODO: is there a better way of enforcing uniqueness than checking
        #       during @register_layer?
        return self._layer_type

    @property
    def points(self) -> xr.DataArray:
        """
        The `~xarray.DataArray` associate with the layer.  If the layer
        has not been generated, then it will be done automatically.
        """
        try:
            return self.item
        except KeyError:
            return self._generate_point_matrix_da()

    @property
    def config(self) -> Dict[str, Any]:
        """
        Dictionary containing the full configuration of the
        :term:`motion layer`.
        """
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

    @property
    def inputs(self) -> Dict[str, Any]:
        """
        A dictionary of the configuration inputs passed during layer
        instantiation.
        """
        return self._inputs

    @abstractmethod
    def _generate_point_matrix(self) -> Union[np.ndarray, xr.DataArray]:
        """
        Generate and return a matrix of points associated with the
        :term:`motion layer`.

        Notes
        -----

        The method should only generate and return the points associated
        with the motion list.  The :attr:`_generate_point_matrix_da`
        method will then validate the array and add it to the
        `xarray.Dataset`.
        """
        ...

    @abstractmethod
    def _validate_inputs(self) -> None:
        """
        Validate the input arguments passed during instantiation.
        These inputs are stored in :attr:`inputs`.
        """
        ...

    def _generate_point_matrix_da(self):
        """
        Generate the :term:`motion layer` array/matrix and add it to
        the `~xarray.Dataset` under the name defined by :attr:`name`.
        """
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
        """
        Re-generated the :term:`motion layer`, i.e. :attr:`points`.
        """
        self._ds[self.name] = self._generate_point_matrix_da()
