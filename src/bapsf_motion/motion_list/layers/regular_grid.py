__all__ = ["GridLayer"]

import numpy as np

from bapsf_motion.motion_list.layers.base import BaseLayer
from bapsf_motion.motion_list.layers.helpers import register_layer


@register_layer
class GridLayer(BaseLayer):
    """
    Class for defining a regularly spaced grid along each of the
    specified axes.
    """
    _layer_type = "grid"

    def __init__(self, ds, limits, steps):
        # assign all, and only, instance variables above the super
        super().__init__(ds, limits=limits, steps=steps)

    def _generate_point_matrix(self):
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
        limits = self.limits
        steps = self.steps
        mspace_ndims = self.mspace_ndims

        # 1st pass on limits validation
        if not isinstance(limits, np.ndarray):
            limits = np.array(limits, dtype=np.float64)

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
                f"or equal to the dimensionallity of motion space {self.mspace_ndims}."
            )
        elif limits.ndim == 1 and limits.shape[0] not in (2, mspace_ndims):
            raise ValueError(
                "Needs to be array_like of size 2 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims}."
            )

        if limits.ndim == 1 or limits.shape[0] == 1:
            # only one limit has been defined, assume this is used for
            # all mspace dimensions
            if limits.ndim == 2:
                limits == limits[0, ...]

            limits = np.repeate(limits[np.newaxis, ...], mspace_ndims, axis=0)

        # 1st pass on steps validation
        if not isinstance(steps, np.ndarray):
            steps = np.array(steps, dtype=np.int32)

        if steps.ndim != 1:
            raise ValueError("Keyword 'steps' needs to be 1D array_like.")
        elif steps.size not in (1, mspace_ndims):
            raise ValueError(
                "Keyword 'steps' must be of size 1 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims}."
            )
        elif steps.size == 1:
            steps = np.repeat(steps, self.mspace_ndims)

        self.limits = limits
        self.steps = steps

    @property
    def limits(self):
        return self.inputs["limits"]

    @limits.setter
    def limits(self, value):
        self.inputs["limits"] = value

    @property
    def steps(self):
        return self.inputs["steps"]

    @steps.setter
    def steps(self, value):
        self.inputs["steps"] = value
