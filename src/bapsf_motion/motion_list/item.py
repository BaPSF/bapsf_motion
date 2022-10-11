__all__ = ["MLItem"]
import xarray as xr


class MLItem:
    __mask_name = "mask"

    def __init__(self, ds: xr.Dataset, base_name, name_pattern):
        self._ds = self._validate_ds(ds)

        self._base_name = base_name
        self._name_pattern = name_pattern
        self._name = self._determine_name()

    @property
    def base_name(self):
        return self._base_name

    @property
    def name_pattern(self):
        return self._name_pattern

    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            return

    @property
    def item(self):
        return self._ds[self.name]

    @property
    def mask(self):
        return self._ds[self.mask_name]

    @property
    def mask_name(self):
        return self.__mask_name

    @property
    def mspace_coords(self):
        return self.mask.coords

    @property
    def mspace_dims(self):
        return self.mask.dims

    @property
    def mspace_ndims(self):
        return len(self.mspace_dims)

    @staticmethod
    def _validate_ds(ds: xr.Dataset):
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
        if self.name is not None:
            return self.name

        names = set(self._ds.data_vars.keys())
        n_existing = 0
        for name in names:
            if self.name_pattern.fullmatch(name) is not None:
                n_existing += 1

        return f"{self.base_name}{n_existing + 1:d}"
