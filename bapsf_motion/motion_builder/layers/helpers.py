"""
Module for helper functions associated with :term:`motion layer`
functionality.
"""
__all__ = ["layer_factory", "register_layer", "layer_registry"]

import inspect
import xarray as xr

from numpydoc.docscrape import NumpyDocString, Parameter
from typing import Dict, List, Set, Type, Union

from bapsf_motion.motion_builder.layers import base

if False:
    # noqa
    # for annotation, does not need real import
    from xarray import Dataset

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
        `~bapsf_motion.motion_builder.layers.base.BaseLayer` and the
        registry key will be taken from
        :attr:`~bapsf_motion.motion_builder.layers.base.BaseLayer.layer_type`.

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
    ~bapsf_motion.motion_builder.layers.base.BaseLayer
        Instantiated motion layer class associated with ``ly_type``.
    """
    # TODO: How to automatically document the available ly_types?
    ex = _LAYER_REGISTRY[ly_type]
    return ex(ds, **settings)


class LayerRegistry:
    _registry = _LAYER_REGISTRY  # type: Dict[str, Type[base.BaseLayer]]

    @property
    def available_layers(self):
        return set(self._registry.keys())

    def get_layer(self, name: str):
        try:
            return self._registry[name]
        except KeyError:
            raise ValueError(
                f"The requested exclusion '{name}' does not exist."
            )

    def get_names_by_dimensionality(self, ndim: int) -> Set[str]:
        return set(
             name
             for name, ly in self._registry.items()
             if ly._dimensionality in (-1, ndim)
        )

    def get_input_parameters(
            self, name: str
    ) -> Dict[str, Dict[str, Union[inspect.Parameter, List[str]]]]:
        ly = self.get_layer(name)
        sig = inspect.signature(ly).parameters.copy()
        sig.pop("ds", None)
        sig.pop("skip_ds_add", None)
        sig.pop("args", None)
        sig.pop("kwargs", None)

        doc = inspect.getdoc(ly)
        ndoc = NumpyDocString(doc)
        ndoc_params = ndoc["Parameters"]  # type: List[Parameter]

        params = {}
        for pname, param in sig.items():
            desc = ""
            for pdesc in ndoc_params:
                if pname == pdesc.name.split(":")[0]:
                    desc = pdesc.desc
                    ndoc_params.remove(pdesc)
                    break

            params[pname] = {
                "param": param,
                "desc": desc,
            }

        return params

    def factory(self, ds: "Dataset", *, _type: str, **settings):
        """
        Factory function for calling and instantiating :term:`motion layer`
        classes from the registry.

        Parameters
        ----------
        ds: `~xarray.DataSet`
            The `~DataSet` being used to construction the motion list.

        _type: str
            Name of the motion layer type.

        settings
            Keyword arguments to be passed to the retrieved motion layer
            class.

        Returns
        -------
        ~bapsf_motion.motion_builder.layers.base.BaseLayer
            Instantiated motion layer class associated with ``ly_type``.
        """
        # TODO: How to automatically document the available ly_types?
        ly = self.get_layer(_type)
        return ly(ds, **settings)


layer_registry = LayerRegistry()
