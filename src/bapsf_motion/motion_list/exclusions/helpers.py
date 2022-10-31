__all__ = ["exclusion_factory", "register_exclusion"]

import inspect

from typing import Type

from bapsf_motion.motion_list.exclusions import base

_EXCLUSION_REGISTRY = {}


def register_exclusion(exclusion_cls: Type[base.BaseExclusion]):

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


def exclusion_factory(ds, *, ex_type, **settings):
    ex = _EXCLUSION_REGISTRY[ex_type]
    return ex(ds, **settings)
