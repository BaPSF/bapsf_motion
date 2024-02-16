"""
Module containing the definition of
:class:`~bapsf_motion.motion_builder.item.MBItem`.
"""
__all__ = ["MBItem"]

import re
import xarray as xr

from typing import Hashable, Tuple

try:
    from xarray.core.types import ErrorOptions
except (ModuleNotFoundError, ImportError):
    ErrorOptions = str


class MBItem:
    r"""
    A base class for any :term:`motion builder` class that will interact
    with the `xarray` `~xarray.Dataset` containing the
    :term:`motion builder` configuration.

    Parameters
    ----------
    ds: `~xarray.Dataset`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    base_name: str
        A string representing the base name for the motion builder item
        in the `~xarray.Dataset` ``ds``.

    name_pattern: str, `re.Pattern`
        A raw string ``r''`` or `re.Pattern` representing the naming
        pattern for associated motion builder items in the
        `~xarray.Dataset`.  For example, if the ``base_name`` is
        ``'player'``, then an appropriate pattern would look like
        ``r'player(?P<number>[0-9]+)'``.

    """

    # TODO:  Can we define a __del__() to properly handle the removal of
    #        the motion builder items from the motion builder dataset...
    #        unfortunately this requires more than just the items
    #        removal, but also an update of the mask

    __mask_name = "mask"

    def __init__(self, ds: xr.Dataset, base_name: str, name_pattern: "re.Pattern"):
        self._ds = self._validate_ds(ds)

        self._base_name = base_name

        # if not isinstance(name_pattern, re.Pattern):
        #     name_pattern = re.Pattern(name_pattern)
        self._name_pattern = re.compile(name_pattern)

        self._name = self._determine_name()

    @property
    def base_name(self) -> str:
        """Base name for associated items in the `~xarray.Dataset`."""
        return self._base_name

    @property
    def name_pattern(self) -> "re.Pattern":
        """
        The naming pattern for motion builder items in the
        `~xarray.Dataset`.
        """
        return self._name_pattern

    @property
    def name(self) -> str:
        """Name of the motion builder item in the `~xarray.Dataset`."""
        return self._name

    @property
    def item(self):
        """
        The representative motion builder item in the `~xarray.Dataset`.
        """
        return self._ds[self.name]

    @property
    def mask(self) -> xr.DataArray:
        """
        A :math:`N`-D `~xarray.DataArray` representing a boolean mask
        of the :term:`motion space`.  The mask is `True` where a
        :term:`probe drive` is allowed to move, and `False` otherwise.
        """
        return self._ds[self.mask_name]

    @property
    def mask_name(self):
        """Name of the :attr:`mask` item it the `~xarray.Dataset`."""
        return self.__mask_name

    @property
    def mspace_coords(self):
        """
        Dictionary-like container of :term:`motion space` coordinates.
        Keys are given by :attr:`mspace_dims`.  Quick access to
        `~xarray.DataArray.coords` of :attr:`mask`.
        """
        return self.mask.coords

    @property
    def mspace_dims(self) -> Tuple[Hashable, ...]:
        """
        Tuple of :term:`motion space` dimension names.  Quick access to
        `~xarray.DataArray.dims` of :attr:`mask`.
        """
        return self.mask.dims

    @property
    def mspace_ndims(self) -> int:
        """
        Dimensionality of the :term:`motion space`.  Synonymous with
        the number of axes of the :term:`probe drive`.
        """
        return len(self.mspace_dims)

    @staticmethod
    def _validate_ds(ds: xr.Dataset) -> xr.Dataset:
        """Validate the given `~xarray.Dataset`."""
        # TODO: make this into a function that can be used by exclusions and layers
        if not isinstance(ds, xr.Dataset):
            raise TypeError(
                f"Expected type xarray.Dataset for argument "
                f"'ds', got type {type(ds)}."
            )

        if "mask" not in ds.data_vars:
            raise ValueError(
                f"The xarray.DataArray 'mask' representing the "
                "boolean mask of the motion space has not been "
                "defined."
            )

        return ds

    def _determine_name(self):
        """
        Determine the name for the motion builder item that will be used
        in the `~xarray.Dataset`.  This is generally the name of the
        `xarray.DataArray`.

        This method will examine the `~xarray.Dataset` of items matching
        :attr:`name_pattern` and generate a unique :attr:`name` for
        the motion builder item.
        """
        try:
            return self.name
        except AttributeError:
            # self._name has not been defined yet
            pass

        names = set(self._ds.data_vars.keys())
        n_existing = 0
        for name in names:
            if self.name_pattern.fullmatch(name) is not None:
                n_existing += 1

        return f"{self.base_name}{n_existing + 1:d}"

    def drop_vars(self, names: str, *, errors: ErrorOptions = "raise"):
        new_ds = self._ds.drop_vars(names, errors=errors)
        self._ds = new_ds
