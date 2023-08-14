"""
Module for helper functions associated with :term:`exclusion layer`
functionality.
"""
__all__ = ["exclusion_factory", "register_exclusion"]

import inspect

from typing import Type

from bapsf_motion.motion_list.exclusions import base

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
        `~bapsf_motion.motion_list.exclusions.base.BaseExclusion` and
        the registry key will be taken from
        :attr:`~bapsf_motion.motion_list.exclusions.base.BaseExclusion.exclusion_type`.

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


def exclusion_factory(ds, *, ex_type: str, **settings):
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
    ~bapsf_motion.motion_list.exclusions.base.BaseExclusion
        Instantiated motion exclusion class associated with ``ex_type``.
    """
    # TODO: How to automatically document the available ex_types?
    ex = _EXCLUSION_REGISTRY[ex_type]
    return ex(ds, **settings)
