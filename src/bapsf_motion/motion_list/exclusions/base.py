__all__ = ["BaseExclusion"]

import numpy as np
import re
import xarray as xr

from abc import ABC, abstractmethod
from typing import List

from bapsf_motion.motion_list.item import MLItem


class BaseExclusion(ABC, MLItem):
    _exclusion_type = NotImplemented  # type: str

    def __init__(self, ds: xr.Dataset, *, skip_ds_add=False, **kwargs):
        self._config_keys = {"type"}.union(set(kwargs.keys()))
        self.inputs = kwargs
        self.skip_ds_add = skip_ds_add
        self.composed_exclusions = []  # type: List[BaseExclusion]

        super().__init__(
            ds=ds,
            base_name="mask_ex",
            name_pattern=re.compile(r"mask_ex(?P<number>[0-9]+)"),
        )

        self._validate_inputs()

        if self.skip_ds_add:
            return

        # store this mask to the Dataset
        self.regenerate_exclusion()

        # update the global mask
        self.update_global_mask()

    @property
    def config(self):
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.exclusion_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

    @property
    def exclusion_type(self):
        return self._exclusion_type

    @property
    def exclusion(self):
        try:
            return self.item
        except KeyError:
            return self._generate_exclusion()

    @abstractmethod
    def _generate_exclusion(self):
        ...

    @abstractmethod
    def _validate_inputs(self):
        ...

    def is_excluded(self, point):
        # True if the point is excluded, False if the point is included
        if len(point) != self.mspace_ndims:
            raise ValueError

        select = {}
        for ii, dim_name in enumerate(self.mspace_dims):
            select[dim_name] = point[ii]

        return not bool(self.exclusion.sel(method="nearest", **select).data)

    def regenerate_exclusion(self):
        if self.skip_ds_add:
            raise RuntimeError(
                f"For exclusion {self.name} skip_ds_add={self.skip_ds_add} and thus "
                f"the exclusion can not be regenerated and updated in the Dataset.  "
                f"To get the exclusion matrix usine the 'ex.exclusion' property."
            )

        self._ds[self.name] = self._generate_exclusion()

    def update_global_mask(self):
        if self.skip_ds_add:
            raise RuntimeError(
                f"For exclusion {self.name} skip_ds_add={self.skip_ds_add} and thus "
                f"the exclusion can not be merged into the global maks."
            )

        self._ds[self.mask_name] = np.logical_and(
            self.mask,
            self.exclusion,
        )
