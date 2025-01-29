"""
Module that defines governor exclusions that cast shadows of existing
exclusions across the motion space.
"""
__all__ = ["Shadow2DExclusion"]

import numpy as np
import xarray as xr

from typing import List, Tuple, Union

from bapsf_motion.motion_builder.exclusions.base import GovernExclusion
from bapsf_motion.motion_builder.exclusions.helpers import register_exclusion


@register_exclusion
class Shadow2DExclusion(GovernExclusion):
    r"""
    Class for defining an :term:`exclusion layer` that shadows existing
    exclusion layers in the :term:`motion builder`.  This is a
    `~bapsf_motion.motion_builder.exclusions.base.GovernExclusion` that
    operates on 2D :term:`motion space`\ 's and will replace the global
    mask with its own.

    **exclusion type:** ``'shadow_2d'``

    Parameters
    ----------
    ds : `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    source_point : :term:`array_like`
        An (x, y) coordinate for the "light" point source that shadows
        the existing exclusion layers in the mask.

    skip_ds_add: bool
        If `True`, then skip generating the `~xarray.DataArray`
        corresponding to the :term:`exclusion layer` and skip adding it
        to the `~xarray.Dataset`. (DEFAULT: `False`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |RunManager| levels.

    Assume we have a 2D motion space that may or may not have additional
    exclusion layers defined.  A configuration of `Shadow2dExclusion`
    would look like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          el = Shadow2DExclusion(ds, source_point=[20, -20])

       .. code-tab:: py Factory Function

          el = exclusion_factory(
              ds,
              ex_type="shadow_2d",
              source_point=[20, -20],
          )

       .. code-tab:: toml TOML

          [...motion_builder.exclusions]
          type = "shadow_2d"
          source_point = [20, -20]

       .. code-tab:: py Dict Entry

          config["motion_builder"]["exclusions"] = {
              "type": "shadow_2d",
              "source_point": [20, -20],
          }

    """
    _exclusion_type = 'shadow_2d'
    _dimensionality = 2

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        source_point: Union[List, Tuple, np.ndarray],
        skip_ds_add: bool = False,
    ):
        # pre-define attributes that will be fully defined by self._validate_inputs()
        self._boundaries = None
        self._insertion_edge_indices = None

        super().__init__(
            ds,
            source_point=source_point,
            skip_ds_add=skip_ds_add,
        )

    @property
    def source_point(self) -> np.ndarray:
        """(X, Y) location of the pivot, probe-insertion point."""
        return self.inputs["source_point"]

    @property
    def boundaries(self) -> np.ndarray:
        """
        `numpy` array containing the points that define the motion
        space boundaries.

        ``boundaries.shape == (4, 2, 2)``

        - ``index_0`` = 4 = the boundary side "ID"
        - ``index_1`` = 2 = start (0) and stop (1) points of the edge
        - ``index_2`` = 2 = (x, y) coordinates of the associated edge point

        """
        return self._boundaries

    @property
    def insertion_edge_indices(self) -> Tuple:
        """
        Tuple of `int` containing the indices of :attr:`boundaries`
        that a probe would pass through when entering the motion space.
        """
        if self._insertion_edge_indices is None:
            self._insertion_edge_indices = ()
        return self._insertion_edge_indices

    def _validate_inputs(self):
        """Validate input arguments."""
        source_point = self.inputs["source_point"]

        if isinstance(source_point, (list, tuple)):
            source_point = np.array(source_point)

        if not isinstance(source_point, np.ndarray):
            raise TypeError(
                f"For argument source_point expected type numpy array, "
                f"got type{type(source_point)}."
            )
        elif source_point.ndim != 1 or source_point.size != 2:
            raise ValueError(
                f"For argument source_point expected a 1D array of "
                f"size 2, but shape {source_point.shape}."
            )
        self.inputs["source_point"] = source_point

        # populate additional attributes
        self._boundaries = self._build_boundaries()
        self._insertion_edge_indices = self._determine_insertion_edge_indices()

    def _generate_exclusion(self) -> Union[np.ndarray, xr.DataArray]:
        """
        Generate and return a boolean array of the same size and
        shape as :attr:`mask` for the :term:`exclusion layer`.
        """
        # no other masks have been defined, so there is nothing to shadow
        if np.all(self.mask):
            return self.mask.copy()

        # all motion space is not accessible
        if np.all(np.logical_not(self.mask)):
            return self.mask.copy()

        # source_point is in motion space and sits in an excluded region
        x_key, y_key = self.mspace_dims
        if (
            not bool(self.insertion_edge_indices)
            and not self.mask.sel(
                **{x_key: self.source_point[0], y_key: self.source_point[1]}
            )
        ):
            _mask = self.mask.copy()
            _mask[...] = False
            return _mask.copy()

        # Generate pool of edges
        # - to pool contains the (x,y) locations for the starting and ending
        #   points of an edge line segment
        edge_pool = self._build_edge_pool(self.mask)

        # Generate corner rays
        # - these are the unique, ordered arrays pointing from the insertion point
        #   to the corners of the edges (defined in edge_pool)
        corner_rays = self._build_corner_rays(edge_pool)

        # Reduce corner rays
        # - remove corner arrays that point to points behind nearer edges
        ray_mask = self._build_corner_ray_mask(corner_rays, edge_pool)
        corner_rays = corner_rays[ray_mask]

        # Build an array of fanned rays from all the corner rays
        fan_rays = self._build_fanned_rays(edge_pool, corner_rays)
        rays = self._merge_corner_and_fan_rays(corner_rays, fan_rays)

        _mask = self._paint_mask(rays)
        return _mask

    @staticmethod
    def _add_to_edge_pool(edge, epool=None) -> Tuple[int, np.ndarray]:
        """Add ``edge`` to a pool of edges ``epool``."""
        # edge.shape == (2, 2)
        # index_0 -> edge point, 0 = start and 1 = stop
        # index_1 -> edge coordinate (0, 1) = (x, y)
        #
        # epool.shape == (N, 2, 2)
        # index_0 -> Num. of edges
        # index_1 -> edge point, 0 = start and 1 = stop
        # index_2 -> edge coordinate (0, 1) = (x, y)
        #
        if epool is None:
            epool = np.array(edge)[np.newaxis, ...]
        else:
            epool = np.concatenate(
                (epool, np.array(edge)[np.newaxis, ...]),
                axis=0,
            )

        return epool.shape[0] - 1, epool

    def _build_boundaries(self):
        """
        Build an array containing the points the define the boundary
        sides of the motion space.
        """
        # Build an edge pool that defines the boundary of the motion space
        # - shape == (4, 2, 2)
        #   - index_0 = 4 = the boundary side "ID"
        #   - index_1 = 2 = start (0) and stop (1) points of the edge
        #   - index_2 = 2 = (x, y) coordinates of the associated edge point
        res = self.mask_resolution
        dx = 0.5 * res[0]
        dy = 0.5 * res[1]

        x_key, y_key = self.mspace_dims
        x_min = self.mspace_coords[x_key][0] - dx
        x_max = self.mspace_coords[x_key][-1] + dx
        y_min = self.mspace_coords[y_key][0] - dy
        y_max = self.mspace_coords[y_key][-1] + dy

        _pool = np.zeros((4, 2, 2))

        # lower horizontal
        _pool[0, 0, :] = [x_min, y_min]
        _pool[0, 1, :] = [x_max, y_min]

        # right vertical
        _pool[1, 0, :] = [x_max, y_min]
        _pool[1, 1, :] = [x_max, y_max]

        # upper horizontal
        _pool[2, 0, :] = [x_max, y_max]
        _pool[2, 1, :] = [x_min, y_max]

        # left vertical
        _pool[3, 0, :] = [x_min, y_max]
        _pool[3, 1, :] = [x_min, y_min]

        return _pool

    def _build_corner_rays(self, edge_pool: np.ndarray) -> np.ndarray:
        """
        Build an array containing vectors that point from the
        :attr:`insertion_point` to the points defined in ``edge_pool``.
        """
        # Returns corner_rays
        # corner_rays.shape == (N, 2)
        # - index_0 = Num. of rays
        # - index_1 = (x, y) of vector
        #
        # collect unique edge points (i.e. unique (x,y) coords of edge
        # segment start and stop locations)
        edge_points = edge_pool.reshape(-1, 2)
        edge_points = np.unique(edge_points, axis=0)

        corner_rays = edge_points - self.source_point

        # sort corner_rays and edge_points corresponding to the ray angle
        delta = edge_points - self.source_point[np.newaxis, :]
        perp_indices = np.where(delta[..., 0] == 0)[0]
        if perp_indices.size > 0:
            delta[perp_indices, 0] = 1  # dx
            delta[perp_indices, 1] = np.inf * (
                    delta[perp_indices, 1] / np.abs(delta[perp_indices, 1])
            )  # dy
        ray_angles = np.arctan(delta[..., 1] / delta[..., 0])
        sort_i = np.argsort(ray_angles)
        corner_rays = corner_rays[sort_i]

        return corner_rays

    def _build_corner_ray_mask(
            self, corner_rays: np.ndarray, edge_pool: np.ndarray
    ) -> np.ndarray:
        """
        Build a boolean array to mask ``corner_rays`` and filer out
        rays that point to locations behind closer edges.
        """

        edge_vectors = edge_pool[..., 1, :] - edge_pool[..., 0, :]

        # determine if a corner_ray intersects an edge that is closer
        # to the insertion point
        # - solving the eqn:
        #
        #   source_point + mu * corner_ray = edge_pool[..., 0, :] + nu * edge_vector
        #
        #   * mu and nu are scalars
        #   * if 0 < mu < 1 and 0 < nu < 1, then the corner_ray passes through a
        #     closer edge to the insertion point
        #
        point_deltas = edge_pool[..., 0, :] - self.source_point
        denominator = np.cross(
            corner_rays, edge_vectors[:, np.newaxis, ...]
        ).swapaxes(0, 1)
        mu_array = np.cross(point_deltas, edge_vectors) / denominator
        nu_array = (
            np.cross(point_deltas[:, np.newaxis, ...], corner_rays).swapaxes(0, 1)
            / denominator
        )
        mu_condition = np.logical_and(mu_array >= 0, mu_array < 1)
        nu_condition = np.logical_and(nu_array >= 0, nu_array <= 1)
        _condition = np.logical_and(mu_condition, nu_condition)
        _count = np.count_nonzero(_condition, axis=1)

        return np.where(_count == 0, True, False)

    def _build_edge_pool(self, mask: xr.DataArray) -> np.ndarray:
        """
        Build an array containing the points (start and stop) of edges
        in the motion space.  An edge is where the mask switches its
        boolean value.
        """
        # Find the (x, y) coordinates for the starting and ending points
        # of an edge in the mask array.  An edge occurs then neighboring
        # cells change values (i.e. switch between True and False)
        res = self.mask_resolution
        pool = None
        x_key, y_key = self.mspace_dims
        x_coord = self.mspace_coords[x_key]
        y_coord = self.mspace_coords[y_key]

        # gather vertical edges
        edge_indices = np.where(np.diff(mask, axis=0))
        ix_array = np.unique(edge_indices[0])

        for ix in ix_array:
            iy_array = edge_indices[1][edge_indices[0] == ix]

            x = x_coord[ix] + 0.5 * res[0]

            if iy_array.size == 1:
                iy = iy_array[0]

                edge = np.array(
                    [
                        [x, y_coord[iy] - 0.5 * res[1]],
                        [x, y_coord[iy] + 0.5 * res[1]],
                    ]
                )
                eid, pool = self._add_to_edge_pool(edge, pool)
            else:
                jumps = np.where(np.diff(iy_array) != 1)[0]

                starts = np.array([0])
                starts = np.concatenate((starts, jumps + 1))
                starts = iy_array[starts]

                stops = np.concatenate((jumps, [iy_array.size - 1]))
                stops = iy_array[stops]

                for iy_start, iy_stop in zip(starts, stops):
                    edge = np.array(
                        [
                            [x, y_coord[iy_start] - 0.5 * res[1]],
                            [x, y_coord[iy_stop] + 0.5 * res[1]],
                        ]
                    )
                    eid, pool = self._add_to_edge_pool(edge, pool)

        # gather horizontal edges
        edge_indices = np.where(np.diff(mask, axis=1))
        iy_array = np.unique(edge_indices[1])

        for iy in iy_array:
            ix_array = edge_indices[0][edge_indices[1] == iy]

            y = y_coord[iy] + 0.5 * res[1]

            if ix_array.size == 1:
                ix = ix_array[0]

                edge = np.array(
                    [
                        [x_coord[ix] - 0.5 * res[0], y],
                        [x_coord[ix] + 0.5 * res[0], y],
                    ]
                )
                eid, pool = self._add_to_edge_pool(edge, pool)
            else:
                jumps = np.where(np.diff(ix_array) != 1)[0]

                starts = np.array([0])
                starts = np.concatenate((starts, jumps + 1))
                starts = ix_array[starts]

                stops = np.concatenate((jumps, [ix_array.size - 1]))
                stops = ix_array[stops]

                for ix_start, ix_stop in zip(starts, stops):
                    edge = np.array(
                        [
                            [x_coord[ix_start] - 0.5 * res[0], y],
                            [x_coord[ix_stop] + 0.5 * res[0], y],
                        ]
                    )
                    eid, pool = self._add_to_edge_pool(edge, pool)

        # gather motion space perimeter edges
        for ii in range(4):
            boundary_side = self.boundaries[ii, ...]
            delta = boundary_side[1, ...] - boundary_side[0, ...]
            edge_type = "horizontal" if np.isclose(delta[1], 0) else "vertical"

            if edge_type == "horizontal":
                edge_vals = mask.sel(**{y_key: boundary_side[0, 1], "method": "nearest"})
            else:
                edge_vals = mask.sel(**{x_key: boundary_side[0, 0], "method": "nearest"})

            compare_val = ii in self.insertion_edge_indices
            _conditional_array = edge_vals if compare_val else np.logical_not(edge_vals)
            if np.all(_conditional_array):
                # perimeter side is not considered an "edge" (i.e. a boundary
                # where True-False state switches
                pass
            elif np.all(np.logical_not(_conditional_array)):
                # whole side is an edge
                eid, pool = self._add_to_edge_pool(boundary_side, pool)
            else:
                # array contain edges and non-edges
                # False entries are edges
                new_edge_indices = np.where(np.diff(_conditional_array))[0] + 1
                if not _conditional_array[0]:
                    # boundary side starts as a new edge ... this is not captured
                    # by np.diff so manually add the first index
                    new_edge_indices = np.insert(new_edge_indices, 0, 0)
                if not _conditional_array[-1]:
                    # boundary side ends as a new edge ... this is not captured
                    # by np.diff so manually add the last index
                    new_edge_indices = np.append(
                        new_edge_indices, _conditional_array.size - 1
                    )

                for jj in range(0, new_edge_indices.size, 2):
                    istart = new_edge_indices[jj]
                    istop = new_edge_indices[jj + 1] - 1

                    if edge_type == "horizontal":
                        new_edge = np.array(
                            [
                                [x_coord[istart] - 0.5 * res[0], boundary_side[0, 1]],
                                [x_coord[istop] + 0.5 * res[0], boundary_side[0, 1]],
                            ],
                        )
                    else:
                        new_edge = np.array(
                            [
                                [boundary_side[0, 0], y_coord[istart] - 0.5 * res[1]],
                                [boundary_side[0, 0], y_coord[istop] + 0.5 * res[1]],
                            ],
                        )

                    eid, pool = self._add_to_edge_pool(new_edge, pool)

        return pool

    def _build_fanned_rays(
        self, edge_pool: np.ndarray, corner_rays: np.ndarray
    ) -> np.ndarray:
        """
        Create an array of fanned rays sourced from ``corner_rays``, and
        only include rays the project to further edges or the motion
        space boundary.
        """

        # calculate angles of corner_rays
        angles = np.arcsin(corner_rays[..., 1] / np.linalg.norm(corner_rays, axis=1))
        corner_ray_angles = np.where(corner_rays[..., 0] >= 0, angles, np.pi - angles)

        # generate fanned rays
        delta_angle = (
            0.01 * np.min(self.mask_resolution)
            / np.linalg.norm(corner_rays, axis=1)
        )

        fan_plus = np.array(
            [
                np.cos(corner_ray_angles + delta_angle),
                np.sin(corner_ray_angles + delta_angle),
            ],
        ).swapaxes(0, 1)

        fan_minus = np.array(
            [
                np.cos(corner_ray_angles - delta_angle),
                np.sin(corner_ray_angles - delta_angle),
            ],
        ).swapaxes(0, 1)

        fan_rays = np.concatenate((fan_plus, fan_minus), axis=0)

        # project fan rays to the nearest edge
        edge_vectors = edge_pool[..., 1, :] - edge_pool[..., 0, :]

        point_deltas = edge_pool[..., 0, :] - self.source_point
        denominator = np.cross(fan_rays, edge_vectors[:, np.newaxis, ...]).swapaxes(0, 1)
        mu_array = np.cross(point_deltas, edge_vectors) / denominator
        nu_array = (
            np.cross(point_deltas[:, np.newaxis, ...], fan_rays).swapaxes(0, 1)
            / denominator
        )

        mu_condition = mu_array > 0
        nu_condition = np.logical_and(nu_array >= 0, nu_array <= 1)
        mask = np.logical_and(mu_condition, nu_condition)

        # Note: rays that do not satisfy the mask conditions project to
        #       infinity.  This happens when the insertion point is not
        #       located in the motion space and a boundary corner is
        #       fanned.
        mu_array[np.logical_not(mask)] = np.inf
        adjusted_mu_array = np.nanmin(mu_array, axis=1)
        fan_rays = adjusted_mu_array[..., None] * fan_rays

        # filter close points before merging
        dx, dy = self.mask_resolution
        double_corner_rays = np.concatenate((corner_rays, corner_rays), axis=0)
        mask = np.logical_and(
            np.isclose(
                fan_rays[..., 0],
                double_corner_rays[..., 0],
                atol=.5 * self.mask_resolution[0],
            ),
            np.isclose(
                fan_rays[..., 1],
                double_corner_rays[..., 1],
                atol=.5 * self.mask_resolution[1],
            ),
        )
        fan_rays = fan_rays[np.logical_not(mask)]

        # filter out np.inf rays
        finite_mask = np.all(np.isfinite(fan_rays), axis=1)
        fan_rays = fan_rays[finite_mask]

        # sort fan rays
        ray_angles = np.arcsin(fan_rays[..., 1] / np.linalg.norm(fan_rays, axis=1))
        ray_angles = np.where(fan_rays[..., 0] >= 0, ray_angles, np.pi - ray_angles)
        sort_i = np.argsort(ray_angles)
        fan_rays = fan_rays[sort_i]

        return fan_rays

    def _determine_insertion_edge_indices(self):
        # Determine the indices (of self.boundaries) that
        # the probe drive would pass through when inserted into the
        # motion space.
        res = self.mask_resolution
        x_key, y_key = self.mspace_dims
        x_coord = self.mspace_coords[x_key]
        y_coord = self.mspace_coords[y_key]

        x_range = [x_coord[0] - 0.5 * res[0], x_coord[-1] + 0.5 * res[0]]
        y_range = [y_coord[0] - 0.5 * res[1], y_coord[-1] + 0.5 * res[1]]

        if (
            (x_range[0] <= self.source_point[0] <= x_range[1])
            and (y_range[0] <= self.source_point[1] <= y_range[1])
        ):
            # insertion point is within the motion space
            return None

        insertion_edge_indices = []

        deltas = self.boundaries[..., 1, :] - self.boundaries[..., 0, :]

        for _orientation, _index in zip(["horizontal", "vertical"], [1, 0]):
            _indices = np.where(np.isclose(deltas[..., _index], 0))[0]
            ii_min, ii_max = (
                _indices
                if (
                    self.boundaries[_indices[0], 0, _index]
                    < self.boundaries[_indices[1], 0, _index]
                )
                else (_indices[1], _indices[0])
            )
            if self.source_point[_index] > self.boundaries[ii_max, 0, _index]:
                insertion_edge_indices.append(ii_max)
            elif self.source_point[_index] < self.boundaries[ii_min, 0, _index]:
                insertion_edge_indices.append(ii_min)

        return tuple(set(insertion_edge_indices))

    @staticmethod
    def _merge_corner_and_fan_rays(corner_rays, fan_rays):
        # merge rays
        _rays = np.concatenate((corner_rays, fan_rays), axis=0)

        # sort rays by angle
        angles = np.arcsin(_rays[..., 1] / np.linalg.norm(_rays, axis=1))
        angles = np.where(_rays[..., 0] >= 0, angles, np.pi - angles)
        sort_i = np.argsort(angles)
        _rays = _rays[sort_i]

        return _rays

    def _paint_mask(self, rays: np.ndarray) -> xr.DataArray:
        # use the set of rays to paint the True areas of the mask
        x_key, y_key = self.mspace_dims
        x_coord = self.mspace_coords[x_key]
        y_coord = self.mspace_coords[y_key]

        rays = np.append(rays, rays[0, ...][None, ...], axis=0)
        endpoints = rays + self.source_point[None, :]

        triangles = np.zeros((rays.shape[0] - 1, 3, 2))
        triangles[..., 0, :] = self.source_point
        triangles[..., 1, :] = endpoints[:-1, :]
        triangles[..., 2, :] = endpoints[1:, :]

        grid_points = np.zeros((x_coord.size, y_coord.size, 2))
        grid_points[..., 0] = np.repeat(
            x_coord.values[..., np.newaxis], y_coord.size, axis=1
        )
        grid_points[..., 1] = np.repeat(
            y_coord.values[np.newaxis, ...], x_coord.size, axis=0
        )

        # This processes uses Barycentric coordinates to determine if a
        # grid point is within the triangle.
        #
        # https://en.wikipedia.org/wiki/Barycentric_coordinate_system
        #
        # lambda shape is (x_size, y_size, N_rays)
        #
        # calculate lambda_3
        numerator = np.cross(
            grid_points[:, :, None, :] - triangles[None, None, :, 0, :],
            (triangles[:, 1, :] - triangles[:, 0, :])[None, None, :, :],
        )
        denominator = np.cross(
            triangles[:, 2, :] - triangles[:, 0, :],
            triangles[:, 1, :] - triangles[:, 0, :]
        )

        zero_mask = denominator == 0
        if np.any(zero_mask):
            # denominator can be zero if all points on the triangle lie
            # on a line
            not_zero_mask = np.logical_not(zero_mask)
            triangles = triangles[not_zero_mask, ...]
            numerator = numerator[..., not_zero_mask]
            denominator = denominator[not_zero_mask]

        lambda_3 = numerator / denominator[None, None, ...]

        # calculate lambda_2
        numerator = np.cross(
            grid_points[:, :, None, :] - triangles[None, None, :, 0, :],
            (triangles[:, 2, :] - triangles[:, 0, :])[None, None, :, :],
        )
        denominator = -denominator
        lambda_2 = numerator / denominator[None, None, ...]

        # calculate lambda_1
        lambda_1 = 1 - lambda_2 - lambda_3

        # generate the conditional for each point in the motion space
        # _conditional.shape = (mspace Nx, mspace Ny, N_rays)
        #
        lambda_1_condition = np.logical_and(lambda_1 >= 0, lambda_1 <= 1)
        lambda_2_condition = np.logical_and(lambda_2 >= 0, lambda_2 <= 1)
        lambda_3_condition = np.logical_and(lambda_3 >= 0, lambda_3 <= 1)
        _condition = np.logical_and(
            np.logical_and(lambda_1_condition, lambda_2_condition),
            lambda_3_condition,
        )

        return self.mask.copy(data=np.any(_condition, axis=2))
