__all__ = ["MotionList"]

import numpy as np
import xarray as xr

from bapsf_motion.motion_list.exclusions import BaseExclusion, CircularExclusion
from bapsf_motion.motion_list.layers import BaseLayer, GridLayer


class MotionList:
    base_names = {
        "layer": BaseLayer.base_name,
        "exclusion": BaseExclusion.base_name,
    }

    def __init__(self, base_region, layers=None, exclusions=None, use_lapd=True):
        self._base = base_region

        shape = []
        coords = {}
        space_coord = []
        for coord in base_region:
            label = coord["label"]
            limits = coord["range"]
            size = coord["num"]

            coords[label] = np.linspace(limits[0], limits[1], num=size)
            space_coord.append(label)
            shape.append(size)
        shape = tuple(shape)

        self._ds = xr.Dataset(
            {"mask": (tuple(coords.keys()), np.ones(shape, dtype=bool))},
            coords=coords,
        )
        self._ds.coords["space"] = space_coord

        self.layers = []
        if layers is not None:
            # add each defined layer
            for layer in layers:
                self.add_layer(**layer)

        self.exclusions = []
        if exclusions is not None:
            # add each defined exclusion
            for exclusion in exclusions:
                self.add_exclusion(**exclusion)

        self.generate()

    def add_layer(self, **settings):
        layer = GridLayer(self._ds, **settings)
        self.layers.append(layer)

    def remove_layer(self, name):
        for ii, layer in enumerate(self.layers):
            if layer.name == name:
                del self.layers[ii]
                self._ds.drop_vars(name)
                break

        self.clear_motion_list()

    def add_exclusion(self, **settings):
        exclusion = CircularExclusion(self._ds, **settings)
        self.exclusions.append(exclusion)

        self._ds["mask"] = np.logical_and(self._ds["mask"], exclusion.mask)

    def remove_exclusion(self, name):
        for ii, exclusion in enumerate(self.exclusions):
            if exclusion.name == name:
                del self.exclusions[ii]
                self._ds.drop_vars(name)
                break

        self.clear_motion_list()
        self.rebuild_mask()

    def is_excluded(self, point):
        # True if the point is excluded, False if the point is included
        if len(point) != self.mspace_ndims:
            raise ValueError

        select = {}
        for ii, dim_name in enumerate(self.mspace_dims):
            select[dim_name] = point[ii]

        return not bool(self.mask.sel(method="nearest", **select).data)

    @staticmethod
    def flatten_points(points):
        flat_ax = np.prod(points.shape[:-1])
        return np.reshape(points, (flat_ax, points.shape[-1]))

    def generate(self):
        # generate the motion list

        for_concatenation = []

        for layer in self.layers:
            points = layer.points.data.copy()
            points = self.flatten_points(points)
            for_concatenation.append(points)

        points = np.concatenate(for_concatenation, axis=0)

        select = {}
        for ii, dim_name in enumerate(self.mask.dims):
            select[dim_name] = points[..., ii]

        mask = np.diag(self.mask.sel(method="nearest", **select))

        self._ds["motion_list"] = xr.DataArray(
            data=points[mask, ...],
            dims=("index", "space")
        )

    def clear_motion_list(self):
        self._ds.drop_vars("motion_list")
        self._ds.drop_dims("index")

    def rebuild_mask(self):
        ...

    def plot_mask(self):
        ...

    @property
    def mask(self) -> xr.DataArray:
        # return the excludion mask, False for excluded, True for okay
        return self._ds["mask"]

    @property
    def motion_list(self):
        # return the generated motion list
        try:
            ml = self._ds["motion_list"]
        except KeyError:
            self.generate()
            ml = self._ds["motion_list"]

        return ml

    @property
    def mspace_coords(self):
        return self.mask.coords

    @property
    def mspace_dims(self):
        return self.mask.dims

    @property
    def mspace_ndims(self):
        return len(self.mspace_dims)
