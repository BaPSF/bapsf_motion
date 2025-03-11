"""
Module that defines the `GridLayer` class.
"""
__all__ = ["GridLayer", "GridCNStepLayer", "GridCNSizeLayer"]
__mlayers__ = ["GridLayer", "GridCNStepLayer", "GridCNSizeLayer"]

import numpy as np
import warnings
import xarray as xr

from typing import List

from bapsf_motion.motion_builder.layers.base import BaseLayer
from bapsf_motion.motion_builder.layers.helpers import register_layer


@register_layer
class GridLayer(BaseLayer):
    """
    Class for defining a regularly spaced grid.  The grid is configured
    by defining the inclusive ``limits`` and the number of points
    ``npoints`` along each dimension.

    **layer type:** ``'grid'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    limits: :term:`array_like`
        A list of min and max pairs for each dimension of the
        :term:`motion space`. Shape ``(N, 2)`` where ``N`` is the
        dimensionality of the motion space.  Each min and max pair
        defines the inclusive range along that associated axis.  For
        example, a 2D space ``limits`` would look like
        ``[[xmin, xmax], [ymin, ymax]]``.

    npoints: :term:`array_like`
        An array-like object containing the number of points in the
        grid along each dimension.  Size ``(N, )`` where ``N`` is
        the dimensionality of the motion space.  Each entry
        indicates the number of points used along the associated
        axis.  For example, a 2D space ``npoints`` would look like
        ``[Nx, Ny]``.

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the motion points and adding it to the
        `~xarray.Dataset`.  This keyword is provided to facilitate
        functionality of composite layers.  (DEFAULT: `False`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |RunManager| levels.

    Assume we have a 2D motion space and want to define a grid of
    points spaced at an interval of 2 ranging from -10 to 10 along
    the first axis and 0 to 20 along the second axis.  This would look
    like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          ly = GridLayer(
              ds,
              limits = [[-10, 10], [0, 20]],
              npoints=[21, 21],
          )

       .. code-tab:: py Factory Function

          ly = layer_factory(
              ds,
              ly_type = "grid",
              **{
                  "limits": [[-10, 10], [0, 20]],
                  "npoints": [21, 21],
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.layers]
          type = "grid"
          limits = [[-10, 10], [0, 20]]
          npoints = [21, 21]

       .. code-tab:: py Dict Entry

          config["motion_builder"]["layers"] = {
              "type": "grid",
              "limits": [[-10, 10], [0, 20]],
              "npoints": [21, 21],
          }
    """
    _layer_type = "grid"
    _dimensionality = -1

    def __init__(
            self,
            ds: xr.Dataset,
            limits: List[List[float]],
            npoints: List[int] = None,
            skip_ds_add: bool = False,
            **kwargs,
    ):
        if npoints is None and "steps" in kwargs.keys():
            warnings.warn(
                f"{self.__class__.__name__}.__init_() no longer uses argument "
                f"'steps', argument has been renamed to 'npoints'.",
                DeprecationWarning,
            )
            npoints = kwargs["steps"]
        elif npoints is None:
            raise TypeError(
                f"{self.__class__.__name__}.__init__() missing 1 required"
                f"positional argument: 'npoints'"
            )

        # assign all, and only, instance variables above the super
        super().__init__(ds, limits=limits, npoints=npoints, skip_ds_add=skip_ds_add)

    def _generate_point_matrix(self):
        """
        Generate and return a matrix of points associated with the
        :term:`motion layer`.
        """
        axs = []
        npoints = []
        for lims, num in zip(self.limits, self.npoints):
            if lims[0] == lims[1]:
                # assume fixed along this axis
                num = 1

            axs.append(
                np.linspace(lims[0], lims[1], num=num)
            )
            npoints.append(num)

        pts = np.meshgrid(*axs, indexing="ij")
        layer = np.empty(tuple(npoints) + (self.mspace_ndims,))
        for ii, ax_pts in enumerate(pts):
            layer[..., ii] = ax_pts

        # return xr.DataArray(layer)
        return layer

    def _validate_inputs(self):
        """
        Validate the input arguments passed during instantiation.
        These inputs are stored in :attr:`inputs`.
        """
        npoints = self._validate_npoints(self.npoints)
        self._set_npoints(npoints)

        limits = self._validate_limits(self.limits)
        self._set_limits(limits)

        # default to 1 point if limits are equal
        mask = limits[..., 0] == limits[..., 1]
        if np.any(mask):
            npoints[mask] = 1

        # limits are NOT equal if npoints is 1
        npoints_mask = npoints == 1
        if np.any(np.logical_xor(npoints_mask, mask)):
            raise ValueError(
                "Keyword `npoints` defines some axes as 1 point, but the "
                "associated `limits` does NOT have an equal min/max pair."
            )

    def _validate_limits(self, limits):
        """Validate the ``limits`` argument."""
        mspace_ndims = self.mspace_ndims

        # force to numpy array
        if not isinstance(limits, np.ndarray):
            limits = np.array(limits, dtype=np.float64)

        # validate
        if (
            not (
                np.issubdtype(limits.dtype, np.floating)
                or np.issubdtype(limits.dtype, np.integer)
            )
        ):
            raise ValueError(
                f"Keyword 'limits' has dtype {limits.dtype}, but "
                f"expected an integer or float dtype."
            )
        elif limits.ndim not in (1, 2):
            raise ValueError(
                "Keyword 'limits' needs to be a 2-element list "
                "or list of 2-element lists."
            )
        elif limits.ndim == 2 and limits.shape[1] != 2:
            raise ValueError(
                "Needs to be a 2-element list"
            )
        elif limits.ndim == 2 and limits.shape[0] not in (1, mspace_ndims):
            raise ValueError(
                "The number of specified limits needs to be one "
                f"or equal to the dimensionality of motion space {self.mspace_ndims}."
            )
        elif limits.ndim == 1 and limits.shape[0] not in (2, mspace_ndims):
            raise ValueError(
                "Needs to be array_like of size 2 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims}."
            )

        # ensure limits go min to max
        limits.sort(axis=1)

        # repeat a single limit across all dimensions
        if limits.ndim == 1 or limits.shape[0] == 1:
            # only one limit has been defined, assume this is used for
            # all mspace dimensions
            if limits.ndim == 2:
                limits = limits[0, ...]

            limits = np.repeat(limits[np.newaxis, ...], mspace_ndims, axis=0)

        return limits

    def _validate_npoints(self, npoints):
        """Validate the ``npoints`` argument."""
        mspace_ndims = self.mspace_ndims

        # force to numpy array
        if not isinstance(npoints, np.ndarray):
            npoints = np.array(npoints, dtype=np.int32)

        # validate
        if not np.issubdtype(npoints.dtype, np.integer):
            raise ValueError(
                f"Keyword 'npoints' has dtype {npoints.dtype}, but "
                f"expected an integer dtype."
            )
        elif npoints.ndim != 1:
            raise ValueError(
                "Argument 'npoints' needs to be 1D array-like, got "
                f"{npoints.ndim}D array like."
            )
        elif npoints.size not in (1, mspace_ndims):
            raise ValueError(
                "Argument 'npoints' must be of size 1 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims},"
                f" got size {npoints.size}."
            )
        elif np.any(npoints <= 0):
            raise ValueError(
                "All elements of 'npoints' must be a positive integer."
            )
        elif npoints.size == 1:
            npoints = np.repeat(npoints, self.mspace_ndims)

        return npoints

    @property
    def limits(self) -> np.ndarray:
        """
        An array of min and max pairs representing the range along
        each :term:`motion space` dimensions that the point layer
        resides in.  Shape ``(N, 2)`` where ``N`` is the dimensionality
        of the motion space.
        """
        return self.inputs["limits"]

    def _set_limits(self, value):
        self.inputs["limits"] = value

    @property
    def npoints(self) -> np.ndarray:
        """
        The number of points used along each dimension of the motion
        space.  Shape ``(N, )`` where ``N`` is the dimensionality of the
        motion space.
        """
        return self.inputs["npoints"]

    def _set_npoints(self, value):
        self.inputs["npoints"] = value

    @property
    def steps(self) -> np.ndarray:
        """
        The number of points used along each dimension of the motion
        space.  Shape ``(N, )`` where ``N`` is the dimensionality of the
        motion space.

        **Deprecated since v0.2.4**
        """
        warnings.warn(
            f"{self.__class__.__name__} no longer uses the property "
            f"'steps', use property 'npoints' instead.",
            DeprecationWarning,
        )
        return self.npoints


@register_layer
class GridCNStepLayer(GridLayer):
    """
    Class for defining a regularly spaced grid.  The grid is configured
    by defining its ``center``, the number of points ``npoints`` along
    each dimension, and the step size ``step_size`` between points.

    **layer type:** ``'grid_CNStep'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    center : :term:`array_like`
        An array-like object containing the center coordinates of the
        grid.  Size ``(N, )`` where ``N`` is the dimensionality of the
        motion space.

    npoints: :term:`array_like`
        An array-like object containing the number of points in the
        grid along each dimension.  Size ``(N, )`` where ``N`` is the
        dimensionality of the motion space.  Each entry indicates the
        number of points used along the associated axis.  For example,
        a 2D space ``npoints`` would look like ``[Nx, Ny]``.

    step_size: :term:`array_like`
        An array-like object containing the step size between grid
        points along each dimension.  Size ``(N, )`` where ``N`` is the
        dimensionality of the motion space.  Each entry indicates the
        step size for the associated axis.  For example, a 2D space
        ``step_size`` would look like ``[dx, dy]``.

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the motion points and adding it to the
        `~xarray.Dataset`.  This keyword is provided to facilitate
        functionality of composite layers.  (DEFAULT: `False`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |RunManager| levels.

    Assume we have a 2D motion space and want to define a grid of
    points centered at `(0, 10)` with 21 points along each dimension,
    and a step size of `.1` along each dimension.  This would  look
    like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          ly = GridCNStepLayer(
              ds,
              center=[0, 10],
              npoints=[21, 21],
              step_size=[.1, .1],
          )

       .. code-tab:: py Factory Function

          ly = layer_factory(
              ds,
              ly_type = "grid_CNStep",
              **{
                  "center": [0, 10],
                  "npoints": [21, 21],
                  "step_size": [.1, .1],
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.layers]
          type = "grid_CNStep"
          center = [0, 10]
          npoints = [21, 21]
          step_size = [0.1, 0.1]

       .. code-tab:: py Dict Entry

          config["motion_builder"]["layers"] = {
              "type": "grid_CNStep",
              "center": [0, 10],
              "npoints": [21, 21],
              "step_size": [.1, .1],
          }
    """
    _layer_type = "grid_CNStep"
    _dimensionality = -1

    def __init__(
        self,
        ds: xr.Dataset,
        center: List[float],
        npoints: List[int],
        step_size: List[float],
        skip_ds_add: bool = False,
    ):
        # assign all, and only, instance variables above the super
        super(GridLayer, self).__init__(
            ds,
            center=center,
            npoints=npoints,
            step_size=step_size,
            skip_ds_add=skip_ds_add,
        )

    def _validate_inputs(self):
        """
        Validate the input arguments passed during instantiation.
        These inputs are stored in :attr:`inputs`.
        """
        center = self._validate_center(self.center)
        self._set_center(center)

        npoints = self._validate_npoints(self.npoints)
        self._set_npoints(npoints)

        step_size = self._validate_step_size(self.step_size)
        self._set_step_size(step_size)

        # Check for zero step_size
        npoints_mask = npoints == 1
        if np.any(step_size[np.logical_not(npoints_mask)] == 0):
            raise ValueError(
                "Keyword 'step_size' has axes with 0 size. Each motion "
                "space axis with more than 1 point needs a physical "
                "step size greater than 0."
            )

        # calculate limits
        limits = np.zeros((center.size, 2), dtype=np.float64)
        _size = (npoints - 1) * step_size
        _size[npoints_mask] = 0
        limits[..., 1] = 0.5 * _size
        limits[..., 0] = -0.5 * _size
        limits = limits + center[..., None]
        limits = self._validate_limits(limits)
        self._set_limits(limits)

    def _validate_center(self, center):
        """Validate the ``center`` argument."""
        mspace_ndims = self.mspace_ndims

        # force into numpy array
        if not isinstance(center, np.ndarray):
            center = np.array(center, dtype=np.float64).squeeze()

        # validate
        if (
            not (
                np.issubdtype(center.dtype, np.floating)
                or np.issubdtype(center.dtype, np.integer)
            )
        ):
            raise ValueError(
                f"Keyword 'center' has dtype {center.dtype}, but "
                f"expected an integer or float dtype."
            )
        elif center.ndim != 1:
            raise ValueError(
                f"Argument 'center' is a 1D array-like object, got a "
                f"{center.ndim}D array."
            )
        elif center.size != mspace_ndims:
            raise ValueError(
                f"Argument 'center' does not have the same "
                f"dimensionality as the motion space, got {center.size}"
                f" and expect {mspace_ndims}."
            )

        return center

    def _validate_step_size(self, step_size):
        """Validate the ``step_size`` argument."""
        mspace_ndims = self.mspace_ndims

        # force to numpy array
        if not isinstance(step_size, np.ndarray):
            step_size = np.array(step_size, dtype=np.float64).squeeze()

        # validate
        if (
            not (
                np.issubdtype(step_size.dtype, np.floating)
                or np.issubdtype(step_size.dtype, np.integer)
            )
        ):
            raise ValueError(
                f"Keyword 'step_size' has dtype {step_size.dtype}, but "
                f"expected an integer or float dtype."
            )
        elif step_size.ndim != 1:
            raise ValueError(
                "Argument 'step_size' needs to be 1D array-like, got "
                f"{step_size.ndim}D array like."
            )
        elif step_size.size not in (1, mspace_ndims):
            raise ValueError(
                "Argument 'step_size' must be of size 1 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims},"
                f" got size {step_size.size}."
            )
        elif step_size.size == 1:
            step_size = np.repeat(step_size, self.mspace_ndims)

        # ensure all values of step_size are position
        step_size = np.abs(step_size)

        return step_size

    @property
    def center(self) -> np.ndarray:
        """Coordinates for the center of the grid."""
        return self.inputs["center"]

    def _set_center(self, value: np.ndarray):
        self.inputs["center"] = value

    @property
    def step_size(self) -> np.ndarray:
        """Grid point steps size along each spacial dimension."""
        return self.inputs["step_size"]

    def _set_step_size(self, value: np.ndarray):
        self.inputs["step_size"] = value


@register_layer
class GridCNSizeLayer(GridCNStepLayer):
    """
    Class for defining a regularly spaced grid.  The grid is configured
    by defining its ``center``, the number of points ``npoints`` along
    each dimension, and the size (or length) ``size`` of each grid side.

    **layer type:** ``'grid_CNSize'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    center : :term:`array_like`
        An array-like object containing the center coordinates of the
        grid.  Size ``(N, )`` where ``N`` is the dimensionality of the
        motion space.

    npoints: :term:`array_like`
        An array-like object containing the number of points in the
        grid along each dimension.  Size ``(N, )`` where ``N`` is the
        dimensionality of the motion space.  Each entry indicates the
        number of points used along the associated axis.  For example,
        a 2D space ``npoints`` would look like ``[Nx, Ny]``.

    size: :term:`array_like`
        An array-like object containing the size (or length) of the grid
        side along each dimension.  Size ``(N, )`` where ``N`` is the
        dimensionality of the motion space.  Each entry indicates the
        size (or length) for the grid along the associated axis.
        For example, a 2D space ``size`` would look like ``[Lx, Ly]``.

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the motion points and adding it to the
        `~xarray.Dataset`.  This keyword is provided to facilitate
        functionality of composite layers.  (DEFAULT: `False`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |RunManager| levels.

    Assume we have a 2D motion space and want to define a grid of
    points centered at `(0, 10)` with 21 points along each dimension,
    and a size of 15 by 20.  This would  look like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          ly = GridCNSizeLayer(
              ds,
              center=[0, 10],
              npoints=[21, 21],
              size=[15, 20],
          )

       .. code-tab:: py Factory Function

          ly = layer_factory(
              ds,
              ly_type = "grid_CNSize",
              **{
                  "center": [0, 10],
                  "npoints": [21, 21],
                  "size": [15, 20],
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.layers]
          type = "grid_CNSize"
          center = [0, 10]
          npoints = [21, 21]
          size = [15, 20]

       .. code-tab:: py Dict Entry

          config["motion_builder"]["layers"] = {
              "type": "grid_CNSize",
              "center": [0, 10],
              "npoints": [21, 21],
              "size": [15, 20],
          }
    """
    _layer_type = "grid_CNSize"
    _dimensionality = -1

    def __init__(
        self,
        ds: xr.Dataset,
        center: List[float],
        npoints: List[int],
        size: List[float],
        skip_ds_add: bool = False,
    ):
        # assign all, and only, instance variables above the super
        super(GridLayer, self).__init__(
            ds,
            center=center,
            npoints=npoints,
            size=size,
            skip_ds_add=skip_ds_add,
        )

    def _validate_inputs(self):
        """
        Validate the input arguments passed during instantiation.
        These inputs are stored in :attr:`inputs`.
        """
        center = self._validate_center(self.center)
        self._set_center(center)

        npoints = self._validate_npoints(self.npoints)
        self._set_npoints(npoints)

        size = self._validate_size(self.size)
        # self._set_size(size)

        # Check for zero size
        npoints_mask = npoints == 1
        if np.any(size[np.logical_not(npoints_mask)] == 0):
            raise ValueError(
                "Keyword 'size' has axes with 0 length. Each motion "
                "space axis with more than 1 point needs a physical "
                "size greater than 0."
            )

        # ensure sizes with 1 point or 0 length
        size[npoints_mask] = 0
        self._set_size(size)

        # calculate step_size
        step_size = size / np.where(npoints_mask, 1, npoints - 1)
        step_size = self._validate_step_size(step_size)
        self._set_step_size(step_size)

        # calculate limits
        limits = np.zeros((center.size, 2), dtype=np.float64)
        _size = (npoints - 1) * step_size
        _size[npoints_mask] = 0
        limits[..., 1] = 0.5 * _size
        limits[..., 0] = -0.5 * _size
        limits = limits + center[..., None]
        limits = self._validate_limits(limits)
        self._set_limits(limits)

    def _validate_size(self, size):
        """Validate the ``size`` argument."""
        mspace_ndims = self.mspace_ndims

        # force into numpy array
        if not isinstance(size, np.ndarray):
            size = np.array(size, dtype=np.float64).squeeze()

        # validate
        if (
            not (
                np.issubdtype(size.dtype, np.floating)
                or np.issubdtype(size.dtype, np.integer)
            )
        ):
            raise ValueError(
                f"Keyword 'size' has dtype {size.dtype}, but "
                f"expected an integer or float dtype."
            )
        elif size.ndim != 1:
            raise ValueError(
                "Argument 'size' needs to be 1D array-like, got "
                f"{size.ndim}D array like."
            )
        elif size.size not in (1, mspace_ndims):
            raise ValueError(
                "Argument 'size' must be of size 1 or equal to the "
                f"dimensionality of the motion space {self.mspace_ndims},"
                f" got size {size.size}."
            )
        elif size.size == 1:
            size = np.repeat(size, self.mspace_ndims)

        # ensure all values of size are position
        size = np.abs(size)

        return size

    @property
    def size(self) -> np.ndarray:
        """Size (or length) of the grid along each spacial dimension."""
        return self.inputs["size"]

    def _set_size(self, value: np.ndarray):
        self.inputs["size"] = value
