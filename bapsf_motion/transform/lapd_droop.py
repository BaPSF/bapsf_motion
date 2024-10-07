__all__ = ["DroopCorrectABC"]

import astropy.units as u

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
from warnings import warn

import numpy as np

from bapsf_motion.actors.drive_ import Drive


class DroopCorrectABC(ABC):
    _probe_shaft_od = NotImplemented  # type: u.Quantity
    _probe_shaft_wall = NotImplemented  # type: u.Quantity
    _probe_shaft_material = NotImplementedError  # type: str
    _dimensionality = NotImplemented  # type: int

    def __init__(self, drive: Drive, **kwargs):
        if isinstance(drive, Drive):
            self._drive = drive  # type: Union[Drive, None]
            self._axes = list(range(drive.naxes))
        elif (
                isinstance(drive, (list, tuple))
                and all(isinstance(dr, (int, str)) for dr in drive)
        ):
            # hidden mode for debugging purposes
            # - In this case drive is a list or tuple of int or str values
            #   that correspond to the axes' names.

            # TODO: ADD A WARNING HERE THAT WE ARE IN A DEBUG MODE

            self._drive = None
            self._axes = drive
        else:
            raise TypeError(
                f"For input argument 'drive' expected type {Drive}, but got type "
                f"{type(drive)}."
            )

        self.inputs = self._validate_inputs(kwargs)
        # self._config_keys = {"type"}.union(set(self.inputs.keys()))

        # self.dependencies = []  # type: List[BaseTransform]

        # validate matrix
        # self._validate_matrix_to_drive()
        # self._validate_matrix_to_motion_space()

    def __call__(self, points, to_points) -> np.ndarray:
        # validate to_coords
        valid_to_points = {"droop", "nondroop", "ndroop", "non-droop"}
        if not isinstance(to_points, str):
            raise TypeError(
                f"For argument 'to_points' expected type string, got type "
                f"{type(to_points)}."
            )
        elif to_points not in valid_to_points:
            raise ValueError(
                f"For argument 'to_points' expected a string value in "
                f"{valid_to_points}, but got {to_points}."
            )

        points = self._condition_points(points)
        adjusted_points = self._convert(points, to_points=to_points)

        return adjusted_points

    @property
    def axes(self):
        """A list of axis identifiers."""
        # TODO: this need to be redone to be more consistent with drive.axes
        return self._axes

    @property
    def naxes(self):
        """
        The number of axes of the probe drive.

        This is the same as the motion space dimensionality.
        """
        return len(self.axes)

    @property
    def dimensionality(self) -> int:
        """
        The designed dimensionality of the transform.  If ``-1``, then
        the transform does not have a fixed dimensionality, and it can
        morph to the associated |Drive|.
        """
        return self._dimensionality

    @property
    def drive(self) -> Union[Drive, None]:
        return self._drive

    @abstractmethod
    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input arguments from class instantiation.

        Parameters
        ----------
        inputs: Dict[str, Any]
            The optional input arguments passed during class
            instantiation.
        """
        ...

    @abstractmethod
    def _convert_to_droop_points(self, points: np.ndarray) -> np.ndarray:
        ...

    @abstractmethod
    def _convert_to_nondroop_points(self, points: np.ndarray) -> np.ndarray:
        ...

    def _condition_points(self, points):
        # make sure points is a numpy array
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        # make sure points is always an N X M matrix
        if points.ndim == 1 and points.size == self.naxes:
            # single point was given
            points = points[np.newaxis, ...]
        elif points.ndim != 2:
            raise ValueError(
                f"Expected a 2D array of shape (N, {self.naxes}) for "
                f"'points', but got a {points.ndim}-D array."
            )
        elif self.naxes not in points.shape:
            raise ValueError(
                f"Expected a 2D array of shape (N, {self.naxes}) for "
                f"'points', but got shape {points.shape}."
            )
        elif points.shape[1] != self.naxes:
            # dimensions are flipped from expected
            points = np.swapaxes(points, 0, 1)

        return points

    def _convert(self, points, to_points):

        if to_points == "droop":
            adjusted_points = self._convert_to_droop_points(points)
        else:  # non-droop points
            adjusted_points = self._convert_to_nondroop_points(points)

        return adjusted_points

