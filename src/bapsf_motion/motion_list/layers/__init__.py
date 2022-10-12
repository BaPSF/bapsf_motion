__all__ = ["BaseLayer", "GridLayer"]

from bapsf_motion.motion_list.layers.base import BaseLayer
from bapsf_motion.motion_list.layers.regular_grid import GridLayer

# TODO: types of layers
#       - Sphere (regular grid & bloom)
#       - Cylindrical (regular grid & bloom)
#       - Circular (regular grid & bloom)
#       - Point list
#       - curvy linear

_LAYERS_DICT = {
    "grid": GridLayer,
}


def layers_factory(ds, *, ly_type, **settings):
    ex = _LAYERS_DICT[ly_type]
    return ex(ds, **settings)
