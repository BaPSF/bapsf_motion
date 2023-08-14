"""
Module that contains all the functionality focused around
:term:`motion exclusions`.
"""
__all__ = [
    "exclusion_factory",
    "register_exclusion",
    "BaseExclusion",
    "CircularExclusion",
    "DividerExclusion",
    "LaPDXYExclusion",
]

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.circular import CircularExclusion
from bapsf_motion.motion_list.exclusions.divider import DividerExclusion
from bapsf_motion.motion_list.exclusions.helpers import (
    exclusion_factory,
    register_exclusion,
)
from bapsf_motion.motion_list.exclusions.lapd import LaPDXYExclusion

# TODO: types of exclusions
#       - Divider (greater/less than a dividing line)
#       - Cone
#       - Port (an LaPD port)
#       - LaPD (a full LaPD setup)
#       - Shadow (specialty to shadow from a given point)
#       - Rectangular
#       - Cylindrical
#       - Sphere
#       - Polygon
