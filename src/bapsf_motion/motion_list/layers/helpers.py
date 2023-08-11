__all__ = ["layer_factory", "register_layer"]

import inspect
import xarray as xr

from typing import Type

from bapsf_motion.motion_list.layers import base

#: The :term:`motion layer` registry.
_LAYER_REGISTRY = {}


def register_layer(layer_cls: Type[base.BaseLayer]):
    """
    A decorator for registering a :term:`motion layer` classes into
    the motion layer registry.

    Parameters
    ----------
    layer_cls:
        The :term:`motion layer` class to be registered.  The class
        has to be a subclass of
        `~bapsf_motion.motion_list.layers.base.BaseLayer` and the
        registry key will be taken from
        :attr:`~bapsf_motion.motion_list.layers.base.BaseLayer.layer_type`.

    Examples
    --------

    .. code-block:: python

        @register_layer
        class MyLayer(BaseLayer):
            ...
    """

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


def layer_factory(ds: xr.Dataset, *, ly_type: str, **settings):
    """
    Factory function for calling and instantiating :term:`motion layer`
    classes from the registry.

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `~DataSet` being used to construction the motion list.

    ly_type: str
        Name of the motion layer type.

    settings
        Keyword arguments to be passed to the retrieved motion layer
        class.

    Returns
    -------
    ~bapsf_motion.motion_list.layers.base.BaseLayer
        Instantiated motion layer class associated with ``ly_type``.
    """
    # TODO: How to automatically document the available ly_types?
    ex = _LAYER_REGISTRY[ly_type]
    return ex(ds, **settings)
