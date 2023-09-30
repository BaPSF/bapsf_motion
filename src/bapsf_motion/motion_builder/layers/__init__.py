"""
Module that contains all the functionality focused around
:term:`motion layers`
"""
__all__ = [
    "layer_factory",
    "register_layer",
    "BaseLayer",
]
__mlayers__ = ["GridLayer"]
__all__ += __mlayers__

from bapsf_motion.motion_builder.layers.base import BaseLayer
from bapsf_motion.motion_builder.layers.regular_grid import GridLayer
from bapsf_motion.motion_builder.layers.helpers import register_layer, layer_factory

# TODO: types of layers
#       - Sphere (regular grid & bloom)
#       - Cylindrical (regular grid & bloom)
#       - Circular (regular grid & bloom)
#       - Point list
#       - curvy linear
