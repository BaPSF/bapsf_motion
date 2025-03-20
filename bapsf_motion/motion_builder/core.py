"""
Module containing the definition of |MotionBuilder|.
"""
__all__ = ["MotionBuilder"]

import numpy as np
import re
import warnings
import xarray as xr

from typing import Any, Dict, List, Optional, Union

try:
    from xarray.core.types import ErrorOptions
except (ModuleNotFoundError, ImportError):
    ErrorOptions = str

from bapsf_motion.motion_builder.item import MBItem
from bapsf_motion.motion_builder.exclusions import (
    exclusion_factory,
    BaseExclusion,
    GovernExclusion,
)
from bapsf_motion.motion_builder.layers import (
    layer_factory,
    BaseLayer,
)
from bapsf_motion.utils.exceptions import ConfigurationWarning

# TODO:  create a sit point, this is a point where the probe will sit when
#        a motion list is finished but other motion lists are still running


class MotionBuilder(MBItem):
    r"""
    A class that manages all the functionality around
    :term:`probe drive` motion in the :term:`motion space`\ .  This
    functionality includes:

    1. Defining the motion space the probe moves in.
    2. Generating the :term:`motion list` for a motion sequence.
    3. Generating motion trajectories to avoid obstacles in the
       motion space.

    Parameters
    ----------
    space
    layers
    exclusions
    layer_to_motionlist_scheme : `str`
        (``'sequential'`` or ``'merge'``) The style in which the point
        layers are combined to form the motion list.  ``'sequential'``
        means that the point layers are added sequentially to form the
        motion list, and ``'merge'`` means the point layers are merged
        together (i.e. removing duplicate points and sorting points) to
        form one "global" motion list. (DEFAULT ``'sequential'``)
    """
    # TODO: ^ fully write out the above docstring

    #: Dictionary of :term:`motion builder item` base names.
    base_names = {
        "layer": BaseLayer.base_name,
        "exclusion": BaseExclusion.base_name,
    }

    # TODO: add method for clearing/removing all exclusions
    # TODO: add method for clearing/removing all layers
    # TODO: add functionality for space modification after instantiation
    # TODO: can there be a lightweight option that trashes the DataArrays
    #       after the motion list is completely defined

    def __init__(
            self,
            space: Union[str, List[Dict[str, Any]]],
            layers: Optional[List[Dict[str, Any]]] = None,
            exclusions: Optional[List[Dict[str, Any]]] = None,
            layer_to_motionlist_scheme: str = "sequential",
    ):
        self._space = self._validate_space(space)

        if layer_to_motionlist_scheme not in ("merge", "sequential"):
            layer_to_motionlist_scheme = "sequential"
        self._layer_to_motionlist_scheme = layer_to_motionlist_scheme

        super().__init__(
            self._build_initial_ds(),
            base_name="motion_builder",
            name_pattern=re.compile(r"motion_builder")
        )

        self._layers = []  # type: List[BaseLayer]
        if layers is not None:
            # add each defined layer
            for layer in layers:
                ly_type = layer.pop("type")
                self.add_layer(ly_type, **layer)

        self._exclusions = []  # type: List[BaseExclusion]
        if exclusions is not None:
            # add each defined exclusion
            for exclusion in exclusions:
                ex_type = exclusion.pop("type")
                self.add_exclusion(ex_type, **exclusion)

        self.generate()

    @property
    def config(self) -> Dict[str, Any]:
        """
        Dictionary containing the full configuration of the
        :term:`motion builder`.
        """
        _config = {
            "space": {},
            "layer_to_motionlist_scheme": self.layer_to_motionlist_scheme,
        }

        # pack the space config
        for ii, item in enumerate(self._space):
            _config["space"][ii] = item

        # pack the exclusion config
        if len(self.exclusions):
            _config["exclusion"] = {}
        for ii, ex in enumerate(self.exclusions):
            _config["exclusion"][ii] = ex.config

        # pack the layer config
        if len(self.layers):
            _config["layer"] = {}
        for ii, ly in enumerate(self.layers):
            _config["layer"][ii] = ly.config

        return _config

    @property
    def exclusions(self) -> List[BaseExclusion]:
        """List of added exclusion layers."""
        return self._exclusions

    @property
    def layers(self) -> List[BaseLayer]:
        """List of added point "motion list" layers."""
        return self._layers

    @property
    def layer_to_motionlist_scheme(self) -> str:
        """
        The style in which the point layers are combined to form the
        motion list.  ``'sequential'`` means that the point layers are
        added sequentially to form the motion list, and ``'merge'``
        means the point layers are merged together (i.e. remove
        duplicate points and sort points) to form one "global" motion
        list.
        """
        return self._layer_to_motionlist_scheme

    @layer_to_motionlist_scheme.setter
    def layer_to_motionlist_scheme(self, value: str) -> None:
        if value not in ("sequential", "merge"):
            return

        self._layer_to_motionlist_scheme = value
        self.generate()

    @staticmethod
    def _validate_space(space: List[Dict[str, Any]]):
        """
        Validate the ``space`` argument given during instantiation.

        See the notes section for |MotionBuilder| for additional details.
        """
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
        """
        Perform the initial build of the `xarray.Dataset` that is used
        for defining and constructing the :term:`motion list`.
        """
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

    def _determine_name(self):
        return self.base_name

    def add_layer(self, ly_type: str, **settings):
        """
        Add a "point" layer to the motion builder.

        Parameters
        ----------
        ly_type: str
            String naming the type of layer trying to be defined.

        settings: Dict[str, Any]
            Dictionary defining the configuration of the "point" layer.
            Key-value pairs should correspond the input arguments of
            the class associated with ``ly_type``.

        Examples
        --------

        The following example creates a layer that defines a grid of
        points that is 11-by-21 and inclusively spans 0 to 30 along
        the first axis and -30 to 30 along the second axis.  In this
        case the steps size along both axes is 3.  A ``"grid"`` layer
        is defined/constructed by the
        `~bapsf_motion.motion_builder.layers.regular_grid.GridLayer` class.

        .. code-block:: python

            mb.add_layer(
                "grid",
                **{
                    "limits": [[0, 30], [, -30, 30]],
                    "steps": [11, 21],
                },
            )

        See Also
        --------
        ~bapsf_motion.motion_builder.layers.helpers.layer_factory
        """
        # TODO: add ref in docstring to documented available layers
        layer = layer_factory(self._ds, ly_type=ly_type, **settings)
        self._layers.append(layer)
        self.clear_motion_list()

    def remove_layer(self, name: str):
        """
        Completely remove a layer from the :term:`motion builder`.

        Parameters
        ----------
        name: str
            Name of the layer to be removed.  The name corresponds
            to the `~xarray.DataArray` name in the motion builder
            `~xarray.Dataset`,
        """
        for ii, layer in enumerate(self.layers):
            if layer.name == name:
                # TODO: can we define a __del__ in BaseLayer that would
                #       handle cleanup for layer classes
                del self._layers[ii]
                self.drop_vars(name)
                break

        self.clear_motion_list()

    def add_exclusion(self, ex_type: str, **settings):
        """
        Add an exclusion "layer" to the motion builder.

        Parameters
        ----------
        ex_type: str
            String naming the type of exclusion to be defined.

        settings: Dict[str, Any]
            Dictionary defining the configuration of the exclusion
            "layer".  Key-value pairs should correspond the input
            arguments of the class associated with ``ex_type``.

        See Also
        --------
        ~bapsf_motion.motion_builder.exclusions.helpers.exclusion_factory
        """
        # TODO: add ref in docstring to documented available layers
        exclusion = exclusion_factory(self._ds, ex_type=ex_type, **settings)

        if not isinstance(exclusion, GovernExclusion):
            self._exclusions.append(exclusion)
        elif (
            len(self.exclusions) == 0
            or not isinstance(self.exclusions[0], GovernExclusion)
        ):
            self._exclusions.insert(0, exclusion)
        else:
            warnings.warn(
                f"The motion builder already has a govern exclusion layer "
                f"({self.exclusions[0]}).  Not adding exclusion layer "
                f"{exclusion}.)",
                ConfigurationWarning
            )

        self.clear_motion_list()
        self.rebuild_mask()

    def remove_exclusion(self, name: str):
        """
        Completely remove an exclusion "layer" from the
        :term:`motion builder`.

        Parameters
        ----------
        name: str
            Name of the exclusion to be removed.  The name corresponds
            to the `~xarray.DataArray` name in the motion builder
            `~xarray.Dataset`,
        """
        for ii, exclusion in enumerate(self._exclusions):
            if exclusion.name == name:
                # TODO: can we define a __del__ in BaseLayer that would
                #       handle cleanup for layer classes
                del self._exclusions[ii]
                self.drop_vars(name)
                break

        self.clear_motion_list()
        self.rebuild_mask()

    def is_excluded(self, point) -> bool:
        """
        Check if ``point`` resides in an excluded region of the
        :term:`motion space` or not.

        Parameters
        ----------
        point: :term:`array_like`
            An :term:`array_like` variable that must have a length
            equal to :attr:`mspace_ndims`.

        Returns
        -------
        bool
            `True` if the point resides in an excluded region of the
            :term:`motion space`, otherwise `False`.
        """
        # True if the point is excluded, False if the point is included
        if len(point) != self.mspace_ndims:
            raise ValueError(
                f"The length of `point` ({len(point)}) is not equal to "
                f"the dimensionality of the motion space"
                f"({self.mspace_ndims})."
            )

        select = {}
        for ii, dim_name in enumerate(self.mspace_dims):
            _res = self.mask_resolution[ii]
            _coord = self.mspace_coords[dim_name]
            _point = point[ii]

            if (
                _point < (np.min(_coord) - 0.5 * _res)
                or _point > (np.max(_coord) + 0.5 * _res)
            ):
                # point is outside the motion space
                return True

            select[dim_name] = _point

        return not bool(self.mask.sel(method="nearest", **select).data)

    @staticmethod
    def flatten_points(points):
        r"""
        Take a :math:`M \times \cdots \times N \times S` array
        ``points`` and flatten it into a :math:`Q \times S` array
        where :math:`Q` is the product of
        :math:`M \times \cdots \times N`.

        Parameters
        ----------
        points: :term:`array_like`
            The array to be flattened.
        Returns
        -------
        :term:`array_like`
            The flattened array of ``points``.
        """
        flat_ax = np.prod(points.shape[:-1])
        return np.reshape(points, (flat_ax, points.shape[-1]))

    def generate(self):
        """
        Generated the :term:`motion list` from the currently defined
        :term:`motion space`, :term:`motion layers`, and
        :term:`motion exclusions` in the `~xarray.Dataset`.
        """
        # generate the motion list

        if self.layers is None or not self.layers:
            return

        for_concatenation = []

        for layer in self.layers:
            points = layer.points.data.copy()
            points = self.flatten_points(points)
            for_concatenation.append(points)

        points = np.concatenate(for_concatenation, axis=0)

        if self.layer_to_motionlist_scheme == "merge":
            points = np.unique(points, axis=0)

        mask = self.generate_excluded_mask(points)

        if (
            "motion_list" in self._ds.keys()
            and self._ds["motion_list"].shape[0] != mask.shape[0]
        ):
            self.drop_vars("motion_list")

        self._ds["motion_list"] = xr.DataArray(
            data=points[mask, ...],
            dims=("index", "space")
        )

    def generate_excluded_mask(self, points) -> np.ndarray:
        """
        Generate a boolean mask for the given set of ``points`` where
        `True` indicates the point is valid and `False` the point is
        in an excluded region.  ``points`` should be a
        :math:`M \times n` array where :math:`M` is the number of points
        to examine and :math:`N` is equal to the motion space
        dimensionality.
        """
        if not isinstance(points, np.ndarray):
            points = np.array(points)
        else:
            points = points.copy()

        # make sure points is always an M X N matrix
        if points.ndim == 1 and points.size == self.mspace_ndims:
            # single point was given
            points = points[np.newaxis, ...]
        elif points.ndim != 2:
            raise ValueError(
                f"Expected a 2D array of shape (M, {self.mspace_ndims}) "
                f"for 'points', but got a {points.ndim}-D array."
            )
        elif self.mspace_ndims not in points.shape:
            raise ValueError(
                f"Expected a 2D array of shape (M, {self.mspace_ndims}) "
                f"for 'points', but got shape {points.shape}."
            )
        elif points.shape[1] != self.mspace_ndims:
            # dimensions are flipped from expected
            points = np.swapaxes(points, 0, 1)

        if np.issubdtype(points.dtype, np.floating):
            pass
        elif np.issubdtype(points.dtype, np.integer):
            points = points.astype(np.float64)
        else:
            raise ValueError(
                "Expected a 2D array of dtype integer or floating, but "
                f"got dtype {points.dtype}."
            )

        select = {}
        for ii, dim_name in enumerate(self.mask.dims):
            select[dim_name] = points[..., ii]

        # Note: np.diag is used here since xr.sel will search for all
        #       combinations of given indexers, but we are only
        #       interested in the points along the diagonal of this
        #       forced combination
        mask = np.diag(self.mask.sel(method="nearest", **select))
        return mask

    def get_insertion_point(self) -> Union[np.ndarray, None]:
        """
        Get the insertion point associated with the `GovernExclusion`.
        Returns `None` if no insertion point exists.
        """
        try:
            ex = self.exclusions[0]
        except IndexError:
            return None

        if not isinstance(ex, GovernExclusion):
            return None

        if not hasattr(ex, "insertion_point"):
            return None

        return ex.insertion_point  # noqa

    def clear_motion_list(self):
        """
        Clear/delete the currently constructed :term:`motion list`.
        """
        # TODO: make this more robust...like double checking that are
        #       no point layers defined so a motion list can not exist
        try:
            self.drop_vars("motion_list")
        except ValueError:
            # "motion_list" does not exist yet
            pass

    def rebuild_mask(self):
        """
        Rebuild the current :attr:`mask` from the currently defined
        :term:`motion space` and exclusion layers.
        """
        self.mask[...] = True

        # The govern exclusion is always set to index 0 in self.exclusions.
        # Thus, iterate self.exclusions in reverse order.
        for ex in reversed(self.exclusions):
            ex.update_global_mask()

    def plot_mask(self):
        # TODO: define method to plot motion space mask, i.e. self.mask
        ...

    @property
    def motion_list(self) -> Union[xr.DataArray, None]:
        r"""
        Return the current :term:`motion list`.  If the motion list
        has not been generated, then it will be done automatically.
        The returned `~xarray.DataArray` will have a dimensionality of
        :math:`M \times N` when :math:`M` is the number of points to
        move the probe to and :math:`N` is the equal to the motion
        space dimensionality :attr:`mspace_ndims`.
        """
        # return the generated motion list
        try:
            ml = self._ds["motion_list"]
        except KeyError:
            self.rebuild_mask()
            self.generate()
            if "motion_list" not in self._ds:
                ml = None
            else:
                ml = self._ds["motion_list"]

        return ml

    def drop_vars(self, names: str, *, errors: ErrorOptions = "raise"):
        super().drop_vars(names, errors=errors)

        for item in self.exclusions + self.layers:
            item._ds = self._ds
