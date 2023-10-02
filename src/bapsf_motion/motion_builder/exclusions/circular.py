"""
Module that defines the `CircularExclusion` class.
"""
__all__ = ["CircularExclusion"]
__mexclusions__ = ["CircularExclusion"]

import numbers
import numpy as np
import xarray as xr

from bapsf_motion.motion_builder.exclusions.base import BaseExclusion
from bapsf_motion.motion_builder.exclusions.helpers import register_exclusion


@register_exclusion
class CircularExclusion(BaseExclusion):
    """
    Class for defining circular :term:`exclusion layers` in a 2D
    :term:`motion space`.  The excluded space can be defined as
    internal or external to the circle.

    **exclusion type:** ``'circle'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    radius: `~numbers.Real`
        Radius that defines the circular boundary.

    center: 2-D real :term:`array_like`
        A 2-D :term:`array_like` object of real number define the
        location of the circular region center in the
        :term:`motion space`.

    exclude: str
        If ``'inside'``, then the interior of the circular region
        is defined as the excluded space.  (DEFAULT: ``'outside'``)

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

    Assume we have a 2D motion space and want a circular exclusion
    region outside a circle of radius 20 centered at (-1, 2).  This
    would look like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          el = CircularExclusion(
              ds,
              radius = 20,
              center = [-1, 2],
              exclude = "outside",
          )

       .. code-tab:: py Factory Function

          el = exclusion_factory(
              ds,
              ex_type = "circle",
              **{
                  "radius": 20,
                  "center": [-1, 2],
                  "exclude": "outside",
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.exclusions]
          type = "circle"
          radius = 20
          center = [-1, 20]
          exclude = "outside"

       .. code-tab:: py Dict Entry

          config["motion_builder"]["exclusions"] = {
              "type": "circle",
              "radius": 20,
              "center": [-1, 20],
              "exclude": "outside",
          }
    """
    # TODO: Can this class be extend to a N-D motion space.
    _exclusion_type = "circle"

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        radius,
        center=None,
        exclude: str = "outside",
        skip_ds_add: bool = False,
    ):
        super().__init__(
            ds,
            skip_ds_add=skip_ds_add,
            radius=radius,
            center=center,
            exclude_region=exclude,
        )

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

        condition = (
            (coords[0] - self.center[0]) ** 2 + (coords[1] - self.center[1]) ** 2
            > self.radius ** 2
        )
        mask = xr.where(condition, False, True)
        return mask if self.exclude_region == "outside" else np.logical_not(mask)

    def _validate_inputs(self):
        """Validate input arguments."""
        # TODO: fill-out full conditioning of inputs
        if self.exclude_region not in ("outside", "inside"):
            raise ValueError

        self.inputs["radius"] = np.abs(self.radius)

        center = self.center
        self.inputs["center"] = (0.0, 0.0) if center is None else center

    @property
    def radius(self) -> numbers.Real:
        """Radius of the exclusion circle."""
        return self.inputs["radius"]

    @property
    def center(self):
        """
        Array like :term:`motion space` coordinates of the center of
        the exclusion circle.
        """
        return self.inputs["center"]

    @property
    def exclude_region(self) -> str:
        """
        ``'inside'`` for an interior excluded region and ``'outside'``
        for and exterior excluded region.
        """
        return self.inputs["exclude_region"]
