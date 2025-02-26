"""
Module that defines the `GridLayer` class.
"""
__all__ = ["GridLayer"]
__mlayers__ = ["GridLayer"]

import numpy as np
import xarray as xr

from typing import List

from bapsf_motion.motion_builder.layers.base import BaseLayer
from bapsf_motion.motion_builder.layers.helpers import register_layer


@register_layer
class GridLayer(BaseLayer):
    """
    Class for defining a regularly spaced grid along each of the
    specified axes.  The generated points are inclusive of the
    specified ``limits``.

    **layer type:** ``'grid'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    limits: :term:`array_like`
        A list of min and max pairs for each dimension of the
        :term:`motion space` indicating the min and max span of the
        layer.

    steps: List[int]
        A list of equal length to ``limits`` indicating how many points
        should be used along each dimension of the :term:`motion space`.

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |RunManager| levels.

    Assume we have a 2D motion space and want to define a grid of
    points spaced at an interval of 2 ranging from -10 to 10 along
    the first axis and 0 to 20 along the second axis.  This would look
    like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          ly = GridLayer(
              ds,
              limits = [[-10, 10], [0, 20]],
              steps=[21, 21],
          )

       .. code-tab:: py Factory Function

          ly = layer_factory(
              ds,
              ly_type = "grid",
              **{
                  "limits": [[-10, 10], [0, 20]],
                  "steps": [21, 21],
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.layers]
          type = "grid"
          limits = [[-10, 10], [0, 20]]
          steps = [21, 21]

       .. code-tab:: py Dict Entry

          config["motion_builder"]["layers"] = {
              "type": "grid",
              "limits": [[-10, 10], [0, 20]],
              "steps": [21, 21],
          }
    """
    # TODO: Can the different code types in teh docstring be done with
    #       tabs?
    _layer_type = "grid"
    _dimensionality = -1

    def __init__(
            self,
            ds: xr.Dataset,
            limits: List[List[float]],
            npoints: List[int] = None,
            skip_ds_add: bool = False,
            **kwargs,
    ):
        if npoints is None and "steps" in kwargs.keys():
            warnings.warn(
                f"{self.__class__.__name__}.__init_() no longer uses argument "
                f"'steps', argument has been renamed to 'npoints'.",
                DeprecationWarning,
            )
            npoints = kwargs["steps"]
        elif npoints is None:
            raise TypeError(
                f"{self.__class__.__name__}.__init__() missing 1 required"
                f"positional argument: 'npoints'"
            )

        # assign all, and only, instance variables above the super
        super().__init__(ds, limits=limits, npoints=npoints, skip_ds_add=skip_ds_add)

    def _generate_point_matrix(self):
        """
        Generate and return a matrix of points associated with the
        :term:`motion layer`.
        """
        axs = []
        steps = []
        for lims, num in zip(self.limits, self.steps):
            if lims[0] == lims[1]:
                # assume fixed along this axis
                num = 1

            axs.append(
                np.linspace(lims[0], lims[1], num=num)
            )
            steps.append(num)

        pts = np.meshgrid(*axs, indexing="ij")
        layer = np.empty(tuple(steps) + (self.mspace_ndims,))
        for ii, ax_pts in enumerate(pts):
            layer[..., ii] = ax_pts

        # return xr.DataArray(layer)
        return layer

    def _validate_inputs(self):
        """
        Validate the input arguments passed during instantiation.
        These inputs are stored in :attr:`inputs`.
        """
        limits = self._validate_limits(self.limits)
        self.limits = limits

        npoints = self._validate_npoints(self.npoints)
        self.npoints = npoints

    def _validate_limits(self, limits):
        mspace_ndims = self.mspace_ndims

        # force to numpy array
        if not isinstance(limits, np.ndarray):
            limits = np.array(limits, dtype=np.float64)

        # validate limits
        if limits.ndim not in (1, 2):
            raise ValueError(
                "Keyword 'limits' needs to be a 2-element list "
                "or list of 2-element lists."
            )
        elif limits.ndim == 2 and limits.shape[1] != 2:
            raise ValueError(
                "Needs to be a 2-element list"
            )
        elif limits.ndim == 2 and limits.shape[0] not in (1, mspace_ndims):
            raise ValueError(
                "The number of specified limits needs to be one "
                f"or equal to the dimensionality of motion space {self.mspace_ndims}."
            )
        elif limits.ndim == 1 and limits.shape[0] not in (2, mspace_ndims):
            raise ValueError(
                "Needs to be array_like of size 2 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims}."
            )

        # repeat a single limit across all dimensions
        if limits.ndim == 1 or limits.shape[0] == 1:
            # only one limit has been defined, assume this is used for
            # all mspace dimensions
            if limits.ndim == 2:
                limits = limits[0, ...]

            limits = np.repeat(limits[np.newaxis, ...], mspace_ndims, axis=0)

        return limits

    def _validate_npoints(self, npoints):
        mspace_ndims = self.mspace_ndims

        # force to numpy array
        if not isinstance(npoints, np.ndarray):
            npoints = np.array(npoints, dtype=np.int32)

        # validate
        if npoints.ndim != 1:
            raise ValueError("Keyword 'npoints' needs to be 1D array_like.")
        elif npoints.size not in (1, mspace_ndims):
            raise ValueError(
                "Keyword 'npoints' must be of size 1 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims}."
            )
        elif npoints.size == 1:
            npoints = np.repeat(npoints, self.mspace_ndims)

        return npoints

    @property
    def limits(self) -> np.ndarray:
        """
        An array of min and max pairs representing the range along
        each :term:`motion space` dimensions that the point layer
        resides in.  Shape ``(N, 2)`` where ``N`` is the dimensionality
        of the motion space.
        """
        return self.inputs["limits"]

    @limits.setter
    def limits(self, value):
        # TODO: Add some validation for `value`
        try:
            new_limits = self._validate_limits(value)
        except ValueError:
            return

        self.inputs["limits"] = new_limits

    @property
    def npoints(self) -> np.ndarray:
        """
        The number of points used along each dimension of the motion
        space.  Shape ``(N, )`` where ``N`` is the dimensionality of the
        motion space.
        """
        return self.inputs["npoints"]

    @npoints.setter
    def npoints(self, value):
        try:
            new_npoints = self._validate_npoints(value)
        except ValueError:
            return

        self.inputs["npoints"] = new_npoints

    @property
    def steps(self) -> np.ndarray:
        """
        The number of points used along each dimension of the motion
        space.  Shape ``(N, )`` where ``N`` is the dimensionality of the
        motion space.

        **Deprecated since v0.2.4**
        """
        warnings.warn(
            f"{self.__class__.__name__} no longer uses the property "
            f"'steps', use property 'npoints' instead.",
            DeprecationWarning,
        )
        return self.npoints

    @steps.setter
    def steps(self, value):
        self.npoints = value
