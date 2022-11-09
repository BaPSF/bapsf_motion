__all__ = ["register_transform", "transform_factory"]

import inspect

from typing import Type

from bapsf_motion.transform import base

_TRANSFORM_REGISTRY = {}


def register_transform(transform_cls: Type[base.BaseTransform]):

    if not inspect.isclass(transform_cls):
        raise TypeError(f"Decorated object {transform_cls} is not a class.")
    elif not issubclass(transform_cls, base.BaseTransform):
        raise TypeError(
            f"Decorated clss {transform_cls} is not a subclass of {base.BaseTransform}."
        )

    transform_type = transform_cls._transform_type
    if not isinstance(transform_type, str):
        raise TypeError(
            f"The class attribute '_transform_type' on "
            f"{transform_cls.__qualname__} is of type {type(transform_type)}, "
            f"expected a string."
        )
    elif transform_type in _TRANSFORM_REGISTRY:
        raise ValueError(
            f"Transform type '{transform_type}' is already in the registry."
            f"  Choose a different transform type name for the transform "
            f"class {transform_cls.__qualname__}."
        )

    _TRANSFORM_REGISTRY[transform_type] = transform_cls

    return transform_cls


def transform_factory(drive, *, tr_type, **settings):
    tr = _TRANSFORM_REGISTRY[tr_type]
    return tr(drive, **settings)
