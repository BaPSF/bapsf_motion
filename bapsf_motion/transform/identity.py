"""Module that defines the `IdentityTransform` abstract class."""
__all__ = ["IdentityTransform"]
__transformer__ = ["IdentityTransform"]

import numpy as np

from typing import Any, Dict

from bapsf_motion.transform import base
from bapsf_motion.transform.helpers import register_transform


@register_transform
class IdentityTransform(base.BaseTransform):
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

    Examples
    --------

    The identity transform is super simple to instantiate/configure,
    since there are no defining keywords.

    .. tabs::
       .. code-tab:: py Class Instantiation

          tr = IdentityTransform(drive)

       .. code-tab:: py Factory Function

          tr = transform_factory(drive, tr_type = "identity")

       .. code-tab:: toml TOML

          [...transform]
          type = "identity"

       .. code-tab:: py Dict Entry

          config["transform"] = {"type": "identity"}
    """
    _transform_type = "identity"
    _dimensionality = -1

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return dict()

    @staticmethod
    def _identity_matrix(points: np.ndarray):
        """
        Generate an identity matrix with a zero-ed translation axis.
        """
        matrix = np.identity(points.shape[1] + 1)
        matrix[-1, -1] = 0
        return np.repeat(matrix[np.newaxis, ...], points.shape[0], axis=0)

    def _matrix_to_motion_space(self, points: np.ndarray):
        return self._identity_matrix(points)

    def _matrix_to_drive(self, points: np.ndarray):
        return self._identity_matrix(points)

    def _convert(self, points, to_coords="drive"):
        # __all__ already does validation on points and to_coords, so
        # just return points
        return points
