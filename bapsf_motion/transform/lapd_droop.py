__all__ = ["DroopCorrectABC"]

import astropy.units as u

from abc import ABC, abstractmethod
from typing import Any, Dict

from bapsf_motion.actors.drive_ import Drive


class DroopCorrectABC(ABC):
    _probe_shaft_od = NotImplemented  # type: u.Quantity
    _probe_shaft_wall = NotImplemented  # type: u.Quantity
    _probe_shaft_material = NotImplementedError  # type: str
    _dimensionality = NotImplemented  # type: int

    def __init__(self, drive: Drive, **kwargs):
        if isinstance(drive, Drive):
            self._drive = drive
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
        self._validate_matrix_to_drive()
        self._validate_matrix_to_motion_space()

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
    def _convert_to_droop(self, ):

