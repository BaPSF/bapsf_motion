"""
Module that contains all the functionality focused around
:term:`motion exclusions`.
"""
__all__ = [
    "exclusion_factory",
    "register_exclusion",
    "BaseExclusion",
]
__mexclusions__ = [
    "CircularExclusion",
    "DividerExclusion",
    "LaPDXYExclusion",
]
__all__ += __mexclusions__

from bapsf_motion.motion_builder.exclusions.base import BaseExclusion
from bapsf_motion.motion_builder.exclusions.circular import CircularExclusion
from bapsf_motion.motion_builder.exclusions.divider import DividerExclusion
from bapsf_motion.motion_builder.exclusions.helpers import (
    exclusion_factory,
    register_exclusion,
)
from bapsf_motion.motion_builder.exclusions.lapd import LaPDXYExclusion

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
