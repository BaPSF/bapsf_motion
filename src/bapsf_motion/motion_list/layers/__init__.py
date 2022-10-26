__all__ = [
    "layers_factory",
    "register_layer",
    "BaseLayer",
    "GridLayer",
]

from bapsf_motion.motion_list.layers.base import BaseLayer
from bapsf_motion.motion_list.layers.regular_grid import GridLayer
from bapsf_motion.motion_list.layers.helpers import register_layer, layers_factory

# TODO: types of layers
#       - Sphere (regular grid & bloom)
#       - Cylindrical (regular grid & bloom)
#       - Circular (regular grid & bloom)
#       - Point list
#       - curvy linear
