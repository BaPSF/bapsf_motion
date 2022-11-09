__all__ = ["BaseTransform"]

import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from bapsf_motion.actors import Drive
from bapsf_motion.motion_list import MotionList
from bapsf_motion.transform.helpers import transform_factory


class BaseTransform(ABC):
    _transform_type = NotImplemented  # type: str

    def __init__(
        self,
        axes: Tuple[Union[str, int], ...],
        **kwargs,
    ):
        if not isinstance(axes, (list, tuple)):
            axes  = [axes]

        if not all(isinstance(ax, (int, str)) for ax in axes):
            raise ValueError(
                f"Argument 'axes' needs to be a list or tuple containing "
                f"integers representing the axis' index or strings "
                f"representing the axis' name."
            )

        self._axes = axes

        self.inputs = self._validate_inputs(kwargs)
        self._config_keys = {"type"}.union(set(self.inputs.keys()))

        self.dependencies = []  # type: List[BaseTransform]

        # validate matrix
        matrix = self.matrix([0.0] * len(self.axes))
        if not isinstance(matrix, np.ndarray):
            raise TypeError
        elif matrix.shape != tuple(2 * [len(self.axes) + 1]):
            # matrix needs to be square with each dimension being one size
            # larger than the number axes the matrix transforms...the last
            # dimensions allows for shift translations
            raise ValueError

    @property
    def axes(self):
        return self._axes

    @property
    def transform_type(self):
        return self._transform_type

    @property
    def config(self):
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.transform_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

    @abstractmethod
    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def matrix(self, point):
        # to_coord should have two options "drive" and "motion_space"
        # - to_coord="drive" means to convert from motion space coordinates
        #   to drive coordinates
        # - to_coord="motion_space" converts in the opposite direction as
        #   to_coord="drive"
        #
        # TODO: would to_coord be better as a to_drive that has a boolean value
        ...


class Base2Transform(ABC):
    _transform_type = NotImplemented  # type: str

    # TODO: Possible useful methods
    #       - time to more to point (from current position)
    #       - equalize move movement to next point (est. speed, accel,
    #         and decel so all drive axes finish movement at the same
    #         time)
    #       - est. time to complete motion list (this might be more
    #         suited on the MotionGroup class, or MotionList class)

    def __init__(
        self,
        drive: Drive,
        # *,
        # ml: MotionList = None,
        **kwargs,
    ):
        self._drive = self._validate_drive(drive)
        # self._ml = self._validate_motion_list(ml)

        self.inputs = self._validate_inputs(kwargs)
        self._config_keys = {"type"}.union(set(self.inputs.keys()))

        self.dependencies = []  # type: List[BaseTransform]

    @property
    def transform_type(self):
        return self._transform_type

    @property
    def config(self):
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.transform_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

    @property
    def drive(self):
        return self._drive

    # @property
    # def ml(self):
    #     return self._ml

    @staticmethod
    def _validate_drive(drive: Drive) -> Drive:
        if not isinstance(drive, Drive):
            raise TypeError(
                f"Argument 'drive' expected type "
                f"{Drive.__module__}.{Drive.__qualname__} and got type "
                f"{type(drive)}."
            )

        return drive

    def _validate_motion_list(self, ml: Optional[MotionList]) -> Optional[MotionList]:
        if ml is None:
            return
        elif not isinstance(ml, MotionList):
            raise TypeError(
                f"Argument 'ml' expected type "
                f"{MotionList.__module__}.{MotionList.__qualname__}, and "
                f"got type {type(ml)}."
            )
        elif self.drive.naxes != ml.mspace_ndims:
            raise ValueError(
                f"The given 'drive' object and motion list 'ml' object "
                f" do not have matching dimensions, got "
                f"{self.drive.naxes} and {ml.mspace_ndims} respectively."
            )
        elif set(self.drive.anames) != set(ml.mspace_coords.dims):
            raise ValueError(
                f"The give 'drive' axis names and motion spaces axis "
                f"names do not match, got {set(self.drive.anames)} and "
                f"{set(ml.mspace_coords.dims)} respectively."
            )

        return ml

    @abstractmethod
    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def convert(self, points, to_coord="drive"):
        # to_coord should have two options "drive" and "motion_space"
        # - to_coord="drive" means to convert from motion space coordinates
        #   to drive coordinates
        # - to_coord="motion_space" converts in the opposite direction as
        #   to_coord="drive"
        #
        # TODO: would to_coord be better as a to_drive that has a boolean value
        ...


class TransformRule:
    def __init__(self, drive, axes, method, **kwargs):
        self._drive = drive
        self._axes = axes
        tr = transform_factory(drive, tr_type=method, **kwargs)


class Transform(BaseTransform):
    def __init__(self):
        ...
