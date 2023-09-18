"""Module that defines the `IdentityTransform` abstract class."""
__all__ = ["IdentityTransform"]
__transformer__ = ["IdentityTransform"]

import numpy as np

from typing import Any, Dict

from bapsf_motion.transform.base import BaseTransform
from bapsf_motion.transform.helpers import register_transform


@register_transform
class IdentityTransform(BaseTransform):
    """
    Class that defines an Identity coordinate transform, i.e. the
    :term:`motion space` and probe drive coordinates are the same.

    **transform type:** ``'identity'``

    Parameters
    ----------
    drive: |Drive|
        The instance of |Drive| the coordinate transformer will be
        working with.

    kwargs: Dict[str, Any]
        No extra Keywords are required to define this class, however,
        any supplied keywords will be included in the :attr:`config`
        dictionary.
    """
    _transform_type = "identity"

    def __init__(self, drive, **settings):
        super().__init__(drive, **settings)

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return inputs

    def _matrix_to_motion_space(self, points: np.ndarray):
        return

    def _matrix_to_drive(self, points: np.ndarray):
        return

    def _convert(self, points, to_coords="drive"):
        # __all__ already does validation on points and to_coords, so
        # just return points
        return points
