__all__ = ["MotionList"]

import numpy as np
import re
import xarray as xr

from typing import List

from bapsf_motion.motion_list.item import MLItem
from bapsf_motion.motion_list.exclusions import (
    exclusion_factory,
    BaseExclusion,
)
from bapsf_motion.motion_list.layers import (
    layer_factory,
    BaseLayer,
)

# TODO:  create a sit point, this is a point where the probe will sit when
#        a motion list is finished but other motion lists are still running


class MotionList(MLItem):
    base_names = {
        "layer": BaseLayer.base_name,
        "exclusion": BaseExclusion.base_name,
    }

    # TODO: add method for clearing/removing all exclusions
    # TODO: add method for clearing/removing all layers
    # TODO: add functionality for space modification after instantiation

    def __init__(self, space, layers=None, exclusions=None):
        # self._space = space
        self._space = self._validate_space(space)

        super().__init__(
            self._build_initial_ds(),
            base_name="motion_list",
            name_pattern=re.compile(r"motion_list")
        )

        self.layers = []  # type: List[BaseLayer]
        if layers is not None:
            # add each defined layer
            for layer in layers:
                self.add_layer(**layer)

        self.exclusions = []  # type: List[BaseExclusion]
        if exclusions is not None:
            # add each defined exclusion
            for exclusion in exclusions:
                self.add_exclusion(**exclusion)

        self.generate()

    @property
    def config(self):
        _config = {"space": {}}

        # pack the space config
        for sitem in self._space:
            for key, val in sitem.items():
                if key not in _config["space"]:
                    _config["space"][key] = [val]
                else:
                    _config["space"][key].append(val)

        # pack the exclusion config
        if len(self.exclusions):
            _config["exclusion"] = {}
        for ii, ex in enumerate(self.exclusions):
            _config["exclusion"][f"{ii}"] = ex.config

        # pack the layer config
        if len(self.layers):
            _config["layer"] = {}
        for ii, ly in enumerate(self.layers):
            _config["layer"][f"{ii}"] = ly.config

        return _config

    @staticmethod
    def _validate_space(space):
        # TODO: !!! allow `space` to be defined as a list of
        #       !!! dictionaries of a dictionary of lists
        # TODO: incorporate key "resolution" to be able to define step
        #       size instead of "num"
        # TODO: incorporate key "unit" to define units of the axis
        # TODO: does this validation need to be robust enough to
        #       exhaustively cover values for each key-value pair
        #       (e.g. labels given need to be unique)

        if space == "lapd_xy":
            space = (
                {"label": "x", "range": [-55.0, 55.0], "num": 221},
                {"label": "y", "range": [-55.0, 55.0], "num": 221},
            )
        elif space == "lapd_xz":
            # TODO: write error string
            raise NotImplementedError
        elif space == "lapd_xyz":
            # TODO: write error string
            raise NotImplementedError

        if not isinstance(space, (list, tuple)):
            # TODO: write error string
            raise TypeError

        for item in space:
            if not isinstance(item, dict):
                # TODO: write error string
                raise ValueError
            elif set(item.keys()) != {"label", "range", "num"}:
                # TODO: write error string
                raise ValueError

        # by this point `space` should be a list of dictionaries
        return space

    def _build_initial_ds(self):
        shape = []
        coords = {}
        space_coord = []
        for coord in self._space:
            label = coord["label"]
            limits = coord["range"]
            size = coord["num"]

            coords[label] = np.linspace(limits[0], limits[1], num=size)
            space_coord.append(label)
            shape.append(size)
        shape = tuple(shape)

        ds = xr.Dataset(
            {"mask": (tuple(coords.keys()), np.ones(shape, dtype=bool))},
            coords=coords,
        )
        ds.coords["space"] = space_coord

        return ds

    def add_layer(self, **settings):
        ly_type = settings.pop("type")
        layer = layer_factory(self._ds, ly_type=ly_type, **settings)
        self.layers.append(layer)

    def remove_layer(self, name):
        for ii, layer in enumerate(self.layers):
            if layer.name == name:
                del self.layers[ii]
                self._ds.drop_vars(name)
                break

        self.clear_motion_list()

    def add_exclusion(self, **settings):
        ex_type = settings.pop("type")
        exclusion = exclusion_factory(self._ds, ex_type=ex_type, **settings)
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
        self.mask[...] = True

        for ex in self.exclusions:
            ex.update_global_mask()

    def plot_mask(self):
        ...

    @property
    def motion_list(self):
        # return the generated motion list
        try:
            ml = self._ds["motion_list"]
        except KeyError:
            self.rebuild_mask()
            self.generate()
            ml = self._ds["motion_list"]

        return ml
