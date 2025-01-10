"""
Module that contains all the functionality focused around
:term:`motion exclusions`.
"""
__all__ = [
    "exclusion_factory",
    "exclusion_registry",
    "register_exclusion",
    "BaseExclusion",
    "GovernExclusion",
    "Shadow2DExclusion",
]
__mexclusions__ = [
    "CircularExclusion",
    "DividerExclusion",
    "LaPDXYExclusion",
    "Shadow2DExclusion",
]
__all__ += __mexclusions__

from bapsf_motion.motion_builder.exclusions.base import BaseExclusion, GovernExclusion
from bapsf_motion.motion_builder.exclusions.circular import CircularExclusion
from bapsf_motion.motion_builder.exclusions.divider import DividerExclusion
from bapsf_motion.motion_builder.exclusions.helpers import (
    exclusion_factory,
    exclusion_registry,
    register_exclusion,
)
from bapsf_motion.motion_builder.exclusions.lapd import LaPDXYExclusion
from bapsf_motion.motion_builder.exclusions.shadow import Shadow2DExclusion

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
