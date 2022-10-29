__all__ = ["DividerExclusion"]

import numpy as np
import re
import xarray as xr

from typing import Tuple

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.helpers import register_exclusion


@register_exclusion
class DividerExclusion(BaseExclusion):
    _exclusion_type = "divider"
    region_pattern = re.compile(r"(?P<sign>[+|-])e(?P<axis>[0|1])")

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        skip_ds_add=False,
        mb: Tuple[float, float],
        exclude: str = "-e0",
    ):
        super().__init__(
            ds,
            skip_ds_add=skip_ds_add,
            mb=mb,
            exclude_region=exclude,
        )

    @property
    def mb(self):
        return self.inputs["mb"]

    @property
    def exclude_region(self):
        return self.inputs["exclude_region"]

    def _validate_inputs(self):
        _scalar_types = (np.floating, float, np.integer, int)

        if not isinstance(self.mb, (list, tuple)):
            raise TypeError
        elif len(self.mb) != 2:
            raise TypeError
        elif (
            isinstance(self.mb[0], str) and self.mb[0] == "inf"
        ) or np.isinf(self.mb[0]):
            if not isinstance(self.mb[1], _scalar_types):
                raise ValueError

            self.inputs["mb"] = (np.inf, self.mb[1])
        elif not all(isinstance(val, _scalar_types) for val in self.mb):
            raise ValueError

        sign, axis = self._exclude_sign_and_axis()

        if np.isinf(self.mb[0]) and axis == 1:
            raise ValueError
        elif self.mb[0] == 0 and axis == 0:
            raise ValueError

    def _generate_exclusion(self):
        coord_dims = self.mspace_dims
        coords = (
            self.mspace_coords[coord_dims[0]],
            self.mspace_coords[coord_dims[1]],
        )

        slope, intercept = self.mb
        sign, axis = self._exclude_sign_and_axis()

        if np.isinf(slope):
            condition = coords[0] - intercept
        elif slope == 0:
            condition = coords[1] - intercept
        elif axis == 1:
            condition = coords[1] - slope * coords[0] - intercept
        else:
            condition = coords[0] - (coords[1] - intercept) / slope

        condition = condition <= 0 if sign == "-" else condition >= 0
        return xr.where(condition, False, True)

    def _exclude_sign_and_axis(self):
        match = self.region_pattern.fullmatch(self.exclude_region)
        if match is None:
            raise ValueError

        return match.group("sign"), int(match.group("axis"))
