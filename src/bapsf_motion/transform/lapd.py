__all__ = ["LaPDXYTransform"]

import numpy as np

from typing import Any, Dict
from warnings import warn

from bapsf_motion.transform.base import BaseTransform
from bapsf_motion.transform.helpers import register_transform


@register_transform
class LaPDXYTransform(BaseTransform):
    _transform_type = "lapd_xy"

    def __init__(
        self,
        axes,
        *,
        pivot_to_center,
        pivot_to_drive,
        polarity=None,
    ):
        super().__init__(
            axes,
            pivot_to_center=pivot_to_center,
            pivot_to_drive=pivot_to_drive,
            polarity=polarity,
        )

        if len(axes) != 2:
            raise ValueError(
                f"LaPDXYTransform require two axes to operate on, only "
                f"{len(axes)} where specified."
            )

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:

        for key in {"pivot_to_center", "pivot_to_drive"}:
            val = inputs[key]
            if not isinstance(val, (float, np.floating, int, np.integer)):
                raise TypeError(
                    f"Keyword '{key}' expected type float or int, "
                    f"got type {type(val)}."
                )
            elif val < 0.0:
                val = np.abs(val)
                warn(
                    f"Keyword '{val}' is NOt supposed to be negative, "
                    f"assuming the absolute value {val}."
                )
            inputs[key] = val

        polarity = inputs["polarity"]
        if polarity is None:
            polarity = np.array([-1, 1])
        elif not isinstance(polarity, np.ndarray):
            polarity = np.array(polarity)

        if polarity.shape != (2,):
            raise ValueError(
                "Keyword 'polarity' is supposed to be a 2-element "
                "array specifying the polarity of each drive axis, got "
                f"an array of shape {polarity.shape}."
            )
        elif not np.all(np.abs(polarity) == 1):
            raise ValueError(
                "Keyword 'polarity' is supposed to be a 2-element "
                "array of 1 or -1 specifying the polarity of each drive"
                " axis, array has values not equal to 1 or -1."
            )
        inputs["polarity"] = polarity

        return inputs

    def matrix(self, points, to_coords="drive") -> np.ndarray:
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        points = points.squeeze()
        if points.ndim not in (1, 2):
            raise ValueError
        elif points.ndim == 1 and points.size != 2:
            # a single point must have both x and y values
            raise ValueError
        elif points.ndim == 2 and points.shape[1] != 2:
            # if an array of points is given then the second dimension
            # must give x and y values
            raise ValueError

        return super().matrix(points, to_coords=to_coords)

    def _matrix_to_motion_space(self, points: np.ndarray):
        points = self.polarity * points  # type: np.ndarray

        theta = np.arctan(points[..., 1] / self.pivot_to_drive)

        npoints = 1 if points.ndim == 1 else points.shape[0]
        matrix = np.zeros((npoints, 3, 3)).squeeze()
        matrix[..., 0, 0] = -np.cos(theta)
        matrix[..., 0, 2] = self.pivot_to_center * (1.0 - np.cos(theta))
        matrix[..., 1, 0] = np.sin(theta)
        matrix[..., 1, 2] = self.pivot_to_center * np.sin(theta)
        matrix[..., 2, 2] = 1.0

        return matrix

    def _matrix_to_drive(self, points):

        theta = np.arctan(points[..., 1] / (self.pivot_to_center - points[..., 0]))

        npoints = 1 if points.ndim == 1 else points.shape[0]
        matrix = np.zeros((npoints, 3, 3)).squeeze()
        matrix[..., 0, 0] = -1.0 / np.cos(theta)
        matrix[..., 0, 2] = self.pivot_to_center * ((1.0 / np.cos(theta)) - 1)
        matrix[..., 1, 2] = self.pivot_to_drive * np.tan(theta)
        matrix[..., 2, 2] = 1.0

        return matrix

    def convert(self, points, to_coords="drive"):
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        matrix = self.matrix(points, to_coords=to_coords)

        if points.ndim == 1:
            points = np.concatenate((points, [1]))
            return np.matmul(matrix, points)[:2]

        points = np.concatenate(
            (points, np.ones((points.shape[0], 1))),
            axis=1,
        )
        return np.einsum("kmn,kn->km", matrix, points)[..., :2]

    @property
    def pivot_to_center(self):
        return self.inputs["pivot_to_center"]

    @property
    def pivot_to_drive(self):
        return self.inputs["pivot_to_drive"]

    @property
    def polarity(self):
        return self.inputs["polarity"]
