__all__ = ["CircularExclusion"]

import numpy as np
import xarray as xr

from bapsf_motion.motion_list.exclusions.base import BaseExclusion


class CircularExclusion(BaseExclusion):
    def __init__(self, ds: xr.Dataset, radius, center=None, exclude="outside"):
        self.radius = radius
        self.center = (0.0, 0.0) if center is None else center
        self.exclude_region = exclude

        # assign all, and only, instance variables above the super
        # - definition of instance variables is mandatory, otherwise
        #   self._generate_mask will not operate correctly
        super().__init__(ds)

    def _generate_exclusion(self):
        coord_dims = self.mspace_dims
        coords = (
            self.mspace_coords[coord_dims[0]],
            self.mspace_coords[coord_dims[1]],
        )

        condition = (
            (coords[0] - self.center[0]) ** 2 + (coords[1] - self.center[1]) ** 2
            > self.radius ** 2
        )
        mask = xr.where(condition, False, True)
        return mask if self.exclude_region == "outside" else np.logical_not(mask)
