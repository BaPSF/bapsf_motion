__all__ = ["BaseExclusion"]
import numpy as np
import re
import xarray as xr

from abc import ABC, abstractmethod


class BaseExclusion(ABC):
    base_name = "mask_ex"
    name_pattern = re.compile(r"mask_ex(?P<number>[0-9]+)")

    def __init__(self, ds: xr.Dataset):
        self._ds = ds
        self.name = self._determine_name()

        # store this mask to the Dataset
        self._ds[self.name] = self._generate_mask()

        # update the global mask
        self._ds["mask"] = np.logical_and(
            self._ds["mask"],
            self._ds[self.name],
        )

    def _determine_name(self):
        if hasattr(self, "name"):
            return self.name

        names = set(self._ds.data_vars.keys())
        n_existing_masks = 0
        for name in names:
            if self.name_pattern.fullmatch(name) is not None:
                n_existing_masks += 1

        return f"{self.base_name}{n_existing_masks + 1:d}"

    @property
    def mask(self):
        return self._ds[self.name]

    @abstractmethod
    def _generate_mask(self):
        ...

    @abstractmethod
    def is_excluded(self, point):
        ...
