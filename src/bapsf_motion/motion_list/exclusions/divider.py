"""
Module that defines the `DividerExclusion` class.
"""
__all__ = ["DividerExclusion"]
__mexclusions__ = ["DividerExclusion"]

import numbers
import numpy as np
import re
import xarray as xr

from typing import Tuple

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.helpers import register_exclusion


@register_exclusion
class DividerExclusion(BaseExclusion):
    r"""
    Class for defining a divider :term:`exclusion layer` in a 2D
    :term:`motion space`.  A divider exclusion defines a linear
    boundary and then excludes one side of that boundary.

    **exclusion type:** ``'divider'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion list configuration
        is constructed in.

    mb: Tuple[`~numbers.Real`, `~numbers.Real`]
        A 2D :term:array_like` object indicating the slope (index ``0``)
        and y-intercept (index ``1``) of the dividing line.

    exclude: str
        A string matching the pattern ``'[+|-]e[0|1]``.  For example,
        a value of ``'-e0'`` indicates the excluded region resides on
        the negative first axis (``e0``) of the dividing line.  A value
        of ``'+e1'`` indicates the excluded region resides on the
        positive second axis (``e1``) of the dividing line.
        (DEFAULT: ``'-e0'``)

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the :term:`exclusion layer` and skip adding it
        to the `~xarray.Dataset`. (DEFAULT: `False`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |Manager| levels.

    Assume we have a 2D motion space and want to exclude the -X region.
    This would look like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          el = DividerExclusion(
              ds,
              mb = (np.inf, 0),
              exclude = "-e0",
          )

       .. code-tab:: py Factory Function

          el = exclusion_factory(
              ds,
              ex_type = "divider",
              **{
                  "mb": ["inf", 0],
                  "exclude": "-e0",
              },
          )

       .. code-tab:: toml TOML

          [...motion_list.exclusions]
          type = "divider"
          mb = ["inf", 0]
          exclude = "-e0"

       .. code-tab:: py Dict Entry

          config["motion_list"]["exclusions"] = {
              "type": "divider",
              "mb": (np.inf, 0),
              "exclude": "-e0",
          }
    """
    # TODO: Can `exclude` be updated to only take "+" and "-"?
    _exclusion_type = "divider"
    region_pattern = re.compile(r"(?P<sign>[+|-])e(?P<axis>[0|1])")

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        mb: Tuple[float, float],
        exclude: str = "-e0",
        skip_ds_add: bool = False,
    ):
        super().__init__(
            ds,
            skip_ds_add=skip_ds_add,
            mb=mb,
            exclude_region=exclude,
        )

    @property
    def mb(self) -> Tuple[numbers.Real, numbers.Real]:
        """
        Tuple with the slope (index ``0``) and intercept (index ``1``)
        of the dividing  line.
        """
        return self.inputs["mb"]

    @property
    def exclude_region(self) -> str:
        """
        String specifying the excluded region.

        The string follows the pattern ``[+|-]e[0|1]``.  See argument
        ``excluded`` in the class parameters section for further
        details.
        """
        return self.inputs["exclude_region"]

    def _validate_inputs(self):
        """Validate input arguments."""
        _scalar_types = (np.floating, float, np.integer, int)

        # mb argument
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

        # exclude argument
        sign, axis = self._exclude_sign_and_axis()

        if np.isinf(self.mb[0]) and axis == 1:
            raise ValueError
        elif self.mb[0] == 0 and axis == 0:
            raise ValueError

    def _generate_exclusion(self):
        """
        Generate and return the boolean mask corresponding to the
        exclusion configuration.
        """
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
        """
        Pull out and return the sign and axis from the ``exclude`` input
        argument string.
        """
        match = self.region_pattern.fullmatch(self.exclude_region)
        if match is None:
            raise ValueError

        return match.group("sign"), int(match.group("axis"))
