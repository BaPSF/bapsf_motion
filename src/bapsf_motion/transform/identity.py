__all__ = ["IdentityTransform"]

import numpy as np

from typing import Any, Dict

from bapsf_motion.transform.base import BaseTransform
from bapsf_motion.transform.helpers import register_transform


@register_transform
class IdentityTransform(BaseTransform):
    _transform_type = "identity"

    def __init__(self, drive, **settings):
        super().__init__(drive, **settings)

        # naxes = len(self.axes) if self._drive is None else self._drive.naxes
        #
        # if naxes != 2:
        #     raise ValueError(
        #         f"The LaPDXYTransform requires two axes to operate on, the "
        #         f"specified probe drive has {drive.naxes} axes."
        #     )

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return inputs

    def _matrix_to_motion_space(self, points: np.ndarray):
        return 1

    def _matrix_to_drive(self, points: np.ndarray):
        return 1

    def _convert(self, points, to_coords="drive"):
        return points
