"""
Module for helper functions associated with coordinate transform
functionality between the probe :term:`motion space` and the probe
drive coordinate system.
"""
__all__ = ["register_transform", "transform_factory", "transform_registry"]

import inspect

from numpydoc.docscrape import NumpyDocString, Parameter
from typing import Dict, List, Set, Type, Union

from bapsf_motion.transform import base

if False:
    # noqa
    # for annotation, does not need real import
    from bapsf_motion.actors.drive_ import Drive

_TRANSFORM_REGISTRY = {}


def register_transform(transform_cls: Type[base.BaseTransform]):
    """
    A decorator for registering a coordinate transform classes into
    the associated registry.

    Parameters
    ----------
    transform_cls:
        The coordinate transform class to be registered.  The class
        has to be a subclass of
        `~bapsf_motion.transform.base.BaseTransform` and
        the registry key will be taken from
        :attr:`~bapsf_motion.transform.base.BaseTransform.transform_type`.

    Examples
    --------

    .. code-block:: python

        @register_transform
        class MyTransform(BaseTransform):
            ...
    """

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


def transform_factory(drive: "Drive", *, tr_type: str, **settings):
    """
    Factory function for calling and instantiating
    :term:`motion exclusion` classes from the registry.

    Parameters
    ----------
    drive: |Drive|
        The instance of |Drive| the coordinate transformer will be
        working with.

    tr_type: str
        Name of the coordinate transform type.

    settings
        Keyword arguments to be passed to the retrieved coordiante
        transform class.

    Returns
    -------
    ~bapsf_motion.transform.base.BaseTransform
        Instantiated coordinate transform class associated with
        ``tr_type``.
    """
    # TODO: How to automatically document the available ex_types?
    tr = _TRANSFORM_REGISTRY[tr_type]
    return tr(drive, **settings)


class TransformRegistry:
    _registry = _TRANSFORM_REGISTRY  # type: Dict[str, Type[base.BaseTransform]]

    @property
    def available_transforms(self):
        return set(self._registry.keys())

    def get_transform(self, name: str):
        try:
            return self._registry[name]
        except KeyError:
            raise ValueError(
                f"The requested transform {name} does not exist."
            )

    def get_names_by_dimensionality(self, ndim: int) -> Set[str]:
        return {
             name
             for name, tr in self._registry.items()
             if tr._dimensionality in (-1, ndim)
         }

    def get_input_parameters(
        self, name: str
    ) -> Dict[str, Dict[str, Union[inspect.Parameter, List[str]]]]:
        tr = self.get_transform(name)
        sig = inspect.signature(tr).parameters.copy()
        sig.pop("drive", None)
        sig.pop("kwargs", None)

        doc = inspect.getdoc(tr)
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


transform_registry = TransformRegistry()
