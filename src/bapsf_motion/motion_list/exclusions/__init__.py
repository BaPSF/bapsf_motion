__all__ = ["BaseExclusion", "CircularExclusion", "DividerExclusion"]

from bapsf_motion.motion_list.exclusions.base import BaseExclusion
from bapsf_motion.motion_list.exclusions.circular import CircularExclusion
from bapsf_motion.motion_list.exclusions.divider import DividerExclusion

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
