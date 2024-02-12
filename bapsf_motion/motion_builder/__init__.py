"""
Module containing functionality for creating and reading
:term:`motion lists`.
"""
__all__ = ["MotionBuilder", "MBItem"]

from bapsf_motion.motion_builder import exclusions, layers
from bapsf_motion.motion_builder.core import MotionBuilder
from bapsf_motion.motion_builder.item import MBItem

# TODO: create a _validate_ds() function that exclusions and layers
#       can use to validate xarray Datasets
