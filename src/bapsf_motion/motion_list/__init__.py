"""
Module containing functionality for creating and reading
:term:`motion lists`.
"""
__all__ = ["MotionBuilder", "MLItem"]

from bapsf_motion.motion_list import exclusions, layers
from bapsf_motion.motion_list.core import MotionBuilder
from bapsf_motion.motion_list.item import MLItem

# TODO: create a _validate_ds() function that exclusions and layers
#       can use to validate xarray Datasets
