"""
Module that contains all the functionality focused around
:term:`motion layers`
"""
__all__ = [
    "layer_factory",
    "layer_registry",
    "register_layer",
    "BaseLayer",
]
__mlayers__ = ["GridLayer", "GridCNStepLayer", "GridCNSizeLayer"]
__all__ += __mlayers__

from bapsf_motion.motion_builder.layers.base import BaseLayer
from bapsf_motion.motion_builder.layers.regular_grid import (
    GridLayer,
    GridCNStepLayer,
    GridCNSizeLayer,
)
from bapsf_motion.motion_builder.layers.helpers import (
    register_layer,
    layer_factory,
    layer_registry,
)

# TODO: types of layers
#       - Sphere (regular grid & bloom)
#       - Cylindrical (regular grid & bloom)
#       - Circular (regular grid & bloom)
#       - Point list
#       - curvy linear
