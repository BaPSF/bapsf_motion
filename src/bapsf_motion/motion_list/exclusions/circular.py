__all__ = ["CircularExclusion"]

import numpy as np
import xarray as xr

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.helpers import register_exclusion


@register_exclusion
class CircularExclusion(BaseExclusion):
    _exclusion_type = "circle"

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        skip_ds_add=False,
        radius,
        center=None,
        exclude="outside",
    ):
        super().__init__(
            ds,
            skip_ds_add=skip_ds_add,
            radius=radius,
            center=center,
            exclude_region=exclude,
        )

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

    def _validate_inputs(self):
        # TODO: fill-out full conditioning of inputs
        if self.exclude_region not in ("outside", "inside"):
            raise ValueError

        self.inputs["radius"] = np.abs(self.radius)

        center = self.center
        self.inputs["center"] = (0.0, 0.0) if center is None else center

    @property
    def radius(self):
        return self.inputs["radius"]

    @property
    def center(self):
        return self.inputs["center"]

    @property
    def exclude_region(self):
        return self.inputs["exclude_region"]
