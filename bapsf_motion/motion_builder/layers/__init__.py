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
from bapsf_motion.motion_builder.layers.helpers import (
    layer_factory,
    layer_registry,
    register_layer,
)
from bapsf_motion.motion_builder.layers.regular_grid import (
    GridCNSizeLayer,
    GridCNStepLayer,
    GridLayer,
)

# TODO: types of layers
#       - Sphere (regular grid & bloom)
#       - Cylindrical (regular grid & bloom)
#       - Circular (regular grid & bloom)
#       - Point list
#       - curvy linear
