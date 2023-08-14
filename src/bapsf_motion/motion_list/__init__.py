"""
Module containing functionality for creating and reading
:term:`motion lists`.
"""
__all__ = ["MotionList", "MLItem"]

from bapsf_motion.motion_list import exclusions, layers
from bapsf_motion.motion_list.core import MotionList
from bapsf_motion.motion_list.item import MLItem

# TODO: create a _validate_ds() function that exclusions and layers
#       can use to validate xarray Datasets
