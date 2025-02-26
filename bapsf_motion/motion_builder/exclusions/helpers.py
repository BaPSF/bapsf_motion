"""
Module for helper functions associated with :term:`exclusion layer`
functionality.
"""
__all__ = ["exclusion_factory", "register_exclusion", "exclusion_registry"]

import inspect

from numpydoc.docscrape import NumpyDocString, Parameter
from typing import Dict, List, Set, Type, Union

from bapsf_motion.motion_builder.exclusions import base

if False:
    # noqa
    # for annotation, does not need real import
    from xarray import Dataset

_EXCLUSION_REGISTRY = {}


def register_exclusion(exclusion_cls: Type[base.BaseExclusion]):
    """
    A decorator for registering a :term:`exclusion layer` classes into
    the exclusion layer registry.

    Parameters
    ----------
    exclusion_cls:
        The :term:`exclusion layer` class to be registered.  The class
        has to be a subclass of
        `~bapsf_motion.motion_builder.exclusions.base.BaseExclusion` and
        the registry key will be taken from
        :attr:`~bapsf_motion.motion_builder.exclusions.base.BaseExclusion.exclusion_type`.

    Examples
    --------

    .. code-block:: python

        @register_exclusion
        class MyExclusion(BaseExclusion):
            ...
    """

    if not inspect.isclass(exclusion_cls):
        raise TypeError(f"Decorated object {exclusion_cls} is not a class.")
    elif not issubclass(exclusion_cls, base.BaseExclusion):
        raise TypeError(
            f"Decorated clss {exclusion_cls} is not a subclass of {base.BaseExclusion}."
        )

    exclusion_type = exclusion_cls._exclusion_type
    if not isinstance(exclusion_type, str):
        raise TypeError(
            f"The class attribute '_layer_type' on "
            f"{exclusion_cls.__qualname__} is of type {type(exclusion_type)}, "
            f"expected a string."
        )
    elif exclusion_type in _EXCLUSION_REGISTRY:
        raise ValueError(
            f"Layer type '{exclusion_type}' is already in the registry."
            f"  Choose a different layer type name for the layer "
            f"class {exclusion_cls.__qualname__}."
        )

    _EXCLUSION_REGISTRY[exclusion_type] = exclusion_cls

    return exclusion_cls


def exclusion_factory(ds: "Dataset", *, ex_type: str, **settings):
    """
    Factory function for calling and instantiating
    :term:`motion exclusion` classes from the registry.

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `~DataSet` being used to construction the motion list.

    ex_type: str
        Name of the motion exclusion type.

    settings
        Keyword arguments to be passed to the retrieved motion
        exclusion class.

    Returns
    -------
    ~bapsf_motion.motion_builder.exclusions.base.BaseExclusion
        Instantiated motion exclusion class associated with ``ex_type``.
    """
    # TODO: How to automatically document the available ex_types?
    ex = _EXCLUSION_REGISTRY[ex_type]
    return ex(ds, **settings)


class ExclusionRegistry:
    _registry = _EXCLUSION_REGISTRY  # type: Dict[str, Type[base.BaseExclusion]]

    @property
    def available_exclusions(self):
        return set(self._registry.keys())

    def get_exclusion(self, name: str):
        try:
            return self._registry[name]
        except KeyError:
            raise ValueError(
                f"The requested exclusion '{name}' does not exist."
            )

    def get_names_by_dimensionality(self, ndim: int) -> Set[str]:
        return set(
             name
             for name, ex in self._registry.items()
             if ex._dimensionality in (-1, ndim)
        )

    def get_input_parameters(
            self, name: str
    ) -> Dict[str, Dict[str, Union[inspect.Parameter, List[str]]]]:
        ex = self.get_exclusion(name)
        sig = inspect.signature(ex).parameters.copy()
        sig.pop("ds", None)
        sig.pop("skip_ds_add", None)
        sig.pop("args", None)
        sig.pop("kwargs", None)

        doc = inspect.getdoc(ex)
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
        Factory function for calling and instantiating
        :term:`motion exclusion` classes from the registry.

        Parameters
        ----------
        ds: `~xarray.DataSet`
            The `~DataSet` being used to construction the motion list.

        _type: str
            Name of the motion exclusion type.

        settings
            Keyword arguments to be passed to the retrieved motion
            exclusion class.

        Returns
        -------
        ~bapsf_motion.motion_builder.exclusions.base.BaseExclusion
            Instantiated motion exclusion class associated with ``ex_type``.
        """
        # TODO: How to automatically document the available ex_types?
        ex = self.get_exclusion(_type)
        return ex(ds, **settings)


exclusion_registry = ExclusionRegistry()
