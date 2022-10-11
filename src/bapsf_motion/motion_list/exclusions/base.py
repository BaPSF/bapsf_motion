__all__ = ["BaseExclusion"]
import numpy as np
import re
import xarray as xr

from abc import ABC, abstractmethod

from bapsf_motion.motion_list.item import MLItem


class BaseExclusion(ABC, MLItem):
    def __init__(self, ds: xr.Dataset):
        super().__init__(
            ds=ds,
            base_name="mask_ex",
            name_pattern=re.compile(r"mask_ex(?P<number>[0-9]+)"),
        )

        # store this mask to the Dataset
        self._ds[self.name] = self._generate_exclusion()

        # update the global mask
        self.update_global_mask()

    @property
    def exclusion(self):
        return self.item

    @abstractmethod
    def _generate_exclusion(self):
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
        self._ds[self.name] = self._generate_exclusion()

    def update_global_mask(self):
        self._ds[self.mask_name] = np.logical_and(
            self.mask,
            self.exclusion,
        )
