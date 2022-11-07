__all__ = ["BaseTransform"]

import numpy as np

from abc import ABC, abstractmethod
from typing import List

from bapsf_motion.actors import Drive
from bapsf_motion.motion_list import MotionList


class BaseTransform(ABC):
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
        ml: MotionList,
        *,
        drive: Drive = None,
        **kwargs,
    ):
        self._config_keys = {"type"}.union(set(kwargs.keys()))
        self._drive = drive
        self._ml = ml
        self.inputs = kwargs
        self.dependencies = []  # type: List[BaseTransform]

        self._validate_inputs()

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

    @property
    def ml(self):
        return self._ml

    @abstractmethod
    def _validate_inputs(self):
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
