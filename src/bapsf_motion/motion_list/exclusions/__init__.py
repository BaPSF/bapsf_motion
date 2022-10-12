__all__ = [
    "exclusion_factory",
    "BaseExclusion",
    "CircularExclusion",
    "DividerExclusion",
    "LaPDExclusion"
]

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.circular import CircularExclusion
from bapsf_motion.motion_list.exclusions.divider import DividerExclusion
from bapsf_motion.motion_list.exclusions.lapd import LaPDExclusion

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

_EXCLUSION_DICT = {
    "circle": CircularExclusion,
    "divider": DividerExclusion,
    "lapd": LaPDExclusion,
}


def exclusion_factory(ds, *, ex_type, **settings):
    ex = _EXCLUSION_DICT[ex_type]
    return ex(ds, **settings)
