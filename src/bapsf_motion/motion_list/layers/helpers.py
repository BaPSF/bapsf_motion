__all__ = ["layer_factory", "register_layer"]

import inspect

from typing import Type

from bapsf_motion.motion_list.layers import base

_LAYER_REGISTRY = {}


def register_layer(layer_cls: Type[base.BaseLayer]):

    if not inspect.isclass(layer_cls):
        raise TypeError(f"Decorated object {layer_cls} is not a class.")
    elif not issubclass(layer_cls, base.BaseLayer):
        raise TypeError(
            f"Decorated clss {layer_cls} is not a subclass of {base.BaseLayer}."
        )

    layer_type = layer_cls._layer_type
    if not isinstance(layer_type, str):
        raise TypeError(
            f"The class attribute '_layer_type' on "
            f"{layer_cls.__qualname__} is of type {type(layer_type)}, "
            f"expected a string."
        )
    elif layer_type in _LAYER_REGISTRY:
        raise ValueError(
            f"Layer type '{layer_type}' is already in the registry."
            f"  Choose a different layer type name for the layer "
            f"class {layer_cls.__qualname__}."
        )

    _LAYER_REGISTRY[layer_type] = layer_cls

    return layer_cls


def layer_factory(ds, *, ly_type, **settings):
    ex = _LAYER_REGISTRY[ly_type]
    return ex(ds, **settings)
