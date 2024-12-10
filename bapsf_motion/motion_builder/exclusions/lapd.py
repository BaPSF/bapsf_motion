"""
Module that defines the `LaPDXYExclusion` class.
"""
__all__ = ["LaPDXYExclusion"]
__mexclusions__ = ["LaPDXYExclusion"]

import numpy as np
import xarray as xr

from numbers import Real
from typing import Tuple, Union

from bapsf_motion.motion_builder.exclusions.base import GovernExclusion
from bapsf_motion.motion_builder.exclusions.circular import CircularExclusion
from bapsf_motion.motion_builder.exclusions.divider import DividerExclusion
from bapsf_motion.motion_builder.exclusions.helpers import register_exclusion


@register_exclusion
class LaPDXYExclusion(GovernExclusion):
    r"""
    Class for defining the :term`LaPD` :term:`exclusion layer` in a XY
    :term:`motion space`.  This class setups up the typical XY
    exclusion layer for a probe installed on a LaPD ball valve.

    **exclusion type:** ``'lapd_xy'``

    Parameters
    ----------
    ds: `~xarray.DataSet`
        The `xarray` `~xarray.Dataset` the motion builder configuration
        is constructed in.

    diameter: `~numbers.Real`
        Diameter of the :term:`LaPD` chamber.  (DEFAULT: `100`)

    pivot_radius: `~numbers.Real`
        Distance from the ball valve pivot point to the :term:`LaPD`
        center axis.  (DEFAULT: ``58.771``)

    port_location: Union[str, Real]
        A variable indicating which port the probe is located at.  A
        value can be a string of
        :math:`\in` :math:`\{`\ e, east, t, top, w, west, b, bot,
        bottom\ :math:`\}` (case-insensitive) or an angle
        :math:`\in [0,360)`.  An East port would correspond to an
        angle of `0` and a Top port corresponds to an angle of `90`.
        An angle port can be indicated by using the corresponding
        angle, e.g. `45`. (DEFAULT: ``'E'``)

    cone_full_angle:  `~numbers.Real`
        The full angle of range provided by the ball valve.
        (DEFAULT: ``80``)

    include_cone: bool
        If `True`, then include the exclusion crated by the ball valve
        limits.  Otherwise, `False` will only include the chamber wall
        exclusion. (DEFAULT: `True`)

    Examples
    --------

    .. note::
       The following examples include examples for direct instantiation,
       as well as configuration passing at the |MotionGroup| and
       |Manager| levels.

    Assume we have a 2D motion space and want to create the default
    exclusion for a probe deployed on the East port.  This would look
    like:

    .. tabs::
       .. code-tab:: py Class Instantiation

          el = LaPDXYExclusion(ds)

       .. code-tab:: py Factory Function

          el = exclusion_factory(
              ds,
              ex_type = "lapd_xy",
          )

       .. code-tab:: toml TOML

          [...motion_builder.exclusions]
          type = "lapd_xy"

       .. code-tab:: py Dict Entry

          config["motion_builder"]["exclusions"] = {
              "type": "lapd_xy",
          }

    Now, lets deploy a probe on a West port using a ball valve with
    a narrower cone and a more restrictive chamber diameters.

    .. tabs::
       .. code-tab:: py Class Instantiation

          el = LaPDXYExclusion(
              ds,
              diameter = 60,
              port_location = "W",
              cone_full_angle = 60,
          )

       .. code-tab:: py Factory Function

          el = exclusion_factory(
              ds,
              ex_type = "lapd_xy",
              **{
                  "diameter": 60,
                  "port_location": "W",
                  "cone_full_angle": 60,
              },
          )

       .. code-tab:: toml TOML

          [...motion_builder.exclusions]
          type = "lapd_xy"
          diameter = 60
          port_location = "W"
          cone_full_angle = 60

       .. code-tab:: py Dict Entry

          config["motion_builder"]["exclusions"] = {
              "type": "lapd_xy",
              "diameter": 60,
              "port_location": "W",
              "cone_full_angle": 60,
          }
    """
    _exclusion_type = "lapd_xy"
    _dimensionality = 2
    _port_location_to_angle = {
        "e": 0,
        "east": 0,
        "t": 90,
        "top": 90,
        "w": 180,
        "west": 180,
        "b": 270,
        "bottom": 270,
        "bot": 270,
    }

    def __init__(
        self,
        ds: xr.Dataset,
        *,
        diameter: float = 100,
        pivot_radius: float = 58.771,
        port_location: Union[str, float] = "E",
        cone_full_angle: float = 80,
        include_cone: bool = True,
        skip_ds_add: bool = False,
    ):
        super().__init__(
            ds,
            diameter=diameter,
            pivot_radius=pivot_radius,
            port_location=port_location,
            cone_full_angle=cone_full_angle,
            include_cone=include_cone,
            skip_ds_add=skip_ds_add,
        )

    @property
    def diameter(self) -> Real:
        """Diameter of the :term:`LaPD` chamber."""
        return self.inputs["diameter"]

    @property
    def pivot_radius(self) -> Real:
        """
        Distance from the ball valve pivot to the chamber center axis.
        """
        return self.inputs["pivot_radius"]

    @property
    def port_location(self) -> Real:
        """
        Angle [in degrees] corresponding to the port location the probe
        is deployed on.  An angle of 0 corresponds to the East port
        and 90 corresponds to the Top port.
        """
        return self.inputs["port_location"]

    @property
    def cone_full_angle(self) -> Real:
        """
        Full angle of range allowed by the ball valve.
        """
        return self.inputs["cone_full_angle"]

    @property
    def include_cone(self) -> bool:
        """
        `True` if the ball valve angle is added to the exclusion,
        `False` otherwise.
        """
        return self.inputs["include_cone"]

    @property
    def insertion_point(self) -> np.ndarray:
        """(X, Y) location of the pivot, probe-insertion point."""
        return np.array(
            [
                self.pivot_radius * np.cos(np.deg2rad(self.port_location)),
                self.pivot_radius * np.sin(np.deg2rad(self.port_location)),
            ],
        )

    def _validate_inputs(self):
        """Validate input arguments."""
        # TODO: fill-out ValueError messages
        self.inputs["diameter"] = np.abs(self.diameter)

        if not self.include_cone:
            self.inputs.update(
                {
                    "pivot_radius": None,
                    "port_location": None,
                    "cone_full_angle": None,
                }
            )
            return

        self.inputs["pivot_radius"] = np.abs(self.pivot_radius)

        if not isinstance(self.cone_full_angle, (float, int)):
            raise ValueError
        elif 0 <= self.cone_full_angle >= 180:
            raise ValueError

        if isinstance(self.port_location, str):
            if self.port_location.casefold() not in map(
                str.casefold, self._port_location_to_angle
            ):
                raise ValueError

            self.inputs["port_location"] = (
                self._port_location_to_angle[self.port_location.lower()]
            )

        if not isinstance(self.port_location, (float, int)):
            raise TypeError
        elif not (-180 < self.port_location < 360):
            raise ValueError(
                f"The angular port location is {self.port_location}, "
                f"expected a value between (-180, 360) degrees."
            )

    def _get_exclusion_by_name(self, name: str):
        """Get a composed exclusion layer from a given ``name``."""
        if not isinstance(name, str):
            raise ValueError(
                "Can not retrieve exclusion since supplied name is not"
                f" a string, got type {type(name)}."
            )

        for ex in self.composed_exclusions:
            if ex.name == name:
                return ex

        raise ValueError(
            f"Supplied exclusion name '{name}' was not found among "
            f"composed exclusions."
        )

    def _combine_exclusions(self):
        """Combine all sub-exclusions into one exclusion array."""
        ex1 = self._get_exclusion_by_name("chamber")
        ex2 = self._get_exclusion_by_name("divider_port")

        exclusion = np.logical_or(ex1.exclusion, ex2.exclusion)

        for ex in self.composed_exclusions:
            if ex.name in {"chamber", "divider_port"}:
                continue
            exclusion = np.logical_and(
                exclusion,
                ex.exclusion,
            )

        return exclusion

    def _generate_exclusion(self):
        """
        Generate and return the boolean mask corresponding to the
        exclusion configuration.
        """
        ex = CircularExclusion(
            self._ds,
            skip_ds_add=True,
            radius=0.5 * self.diameter,
            center=(0.0, 0.0),
            exclude="outside",
        )
        ex.name = "chamber"
        self.composed_exclusions.append(ex)

        if not self.include_cone:
            return self._combine_exclusions()

        # determine slope for code exclusion
        # - P is considered a point in the LaPD coordinate system
        # - P' is considered a point in the pivot (port) coordinate system
        theta = np.radians(self.port_location)
        alpha = 0.5 * np.radians(self.cone_full_angle)
        pivot_xy = self.insertion_point

        # rotation matrix to go P -> P'
        rot_matrix = np.array(
            [
                [np.cos(theta), -np.sin(theta)],
                [np.sin(theta), np.cos(theta)],
            ],
        )

        # rotation matrix to go P' -> P
        inv_rot_matrix = np.linalg.inv(rot_matrix)

        # unit vectors representing the cone trajectories in P'
        cone_trajectories = {
            "upper": np.array([-np.cos(alpha), np.sin(alpha)]),
            "lower": np.array([-np.cos(alpha), -np.sin(alpha)]),
        }

        # unit vectors representing the cone trajectories in P
        for key, traj in cone_trajectories.items():
            p_traj = np.matmul(traj, inv_rot_matrix)

            slope = p_traj[1] / p_traj[0]
            intercept = pivot_xy[1] - slope * pivot_xy[0]

            sign = 1.0 if key == "upper" else -1.0
            exc_dir = np.matmul(np.array([0.0, sign * 1.0]), inv_rot_matrix)

            axis = 0 if np.abs(exc_dir[0]) > np.abs(exc_dir[1]) else 1
            exclude = f"+e{axis}" if exc_dir[axis] > 0 else f"-e{axis}"

            ex = DividerExclusion(
                self._ds,
                skip_ds_add=True,
                mb=(slope, intercept),
                exclude=exclude,
            )
            ex.name = f"divider_{key}"
            self.composed_exclusions.append(ex)

        # divider representing the port opening
        radius = 0.5 * self.diameter
        beta = np.arcsin(self.pivot_radius * np.sin(alpha) / radius)
        if np.abs(beta) < np.pi / 2:
            beta = np.pi - beta
        beta = np.pi - beta - alpha
        pt1 = radius * np.array([np.cos(theta + beta), np.sin(theta + beta)])
        pt2 = radius * np.array([np.cos(theta - beta), np.sin(theta - beta)])
        slope = (
            np.inf
            if np.equal(pt1[0], pt2[0])
            else (pt1[1] - pt2[1]) / (pt1[0] - pt2[0])
        )
        intercept = pt1[0] if np.isinf(slope) else pt1[1] - slope * pt1[0]
        if np.abs(pivot_xy[0]) / radius > .1:
            sign = f"{pivot_xy[0]:+.1f}"[0]
            sign = "-" if sign == "+" else "+"
            exclude = f"{sign}e0"
        else:
            sign = f"{pivot_xy[1]:+.1f}"[0]
            sign = "-" if sign == "+" else "+"
            exclude = f"{sign}e1"

        ex = DividerExclusion(
            self._ds,
            skip_ds_add=True,
            mb=(slope, intercept),
            exclude=exclude,
        )
        ex.name = f"divider_port"
        self.composed_exclusions.append(ex)

        return self._combine_exclusions()

    def govern_mask(self, mask: xr.DataArray) -> xr.DataArray:
        return self.exclusion
    @staticmethod
    def _add_to_edge_pool(edge, epool=None) -> Tuple[int, np.ndarray]:
        # edge.shape == (2, 2)
        # index_1 -> edge point, 0 = start and 1 = stop
        # index_2 -> edge coordinate (0, 1) = (x, y)
        if epool is None:
            epool = np.array(edge)[np.newaxis, ...]
        else:
            epool = np.concatenate(
                (epool, np.array(edge)[np.newaxis, ...]),
                axis=0,
            )

        return epool.shape[0] - 1, epool

    def _build_edge_pool(self, mask: xr.DataArray) -> np.ndarray:
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

        # TODO: add perimeter edges
        # - I [Erik] do not think this is needed since it is logical to
        #   assume the true-ness value stays constant across the
        #   boundary

        return pool

    def create_shadow_mask(self) -> xr.DataArray:
        # we only want to shadow non-LaPDXYExclusion masks

        # no other masks have been defined, so there is nothing to shadow
        if np.all(self.mask):
            return self.mask

        # Build shadow mask
        # 1. Collect a pool of points defining the start and stop of an edge (edge_pool)
        # 2. Build an array of corner arrays that point from the insertion point to each edge point
        # 3.

        # Generate pool of edges
        # - to pool contains the (x,y) locations for the starting and ending
        #   points of an edge line segment
        edge_pool = self._build_edge_pool(self.mask)

        # collect unique edge points (i.e. unique (x,y) coords of edge
        # segment start and stop locations)
        edge_points = edge_pool.reshape(-1, 2)
        edge_points = np.unique(edge_points, axis=0)

        corner_rays = edge_points - self.insertion_point

        # sort corner_rays and edge_points corresponding to the ray angle
        delta = edge_points - self.insertion_point[np.newaxis, :]
        perp_indices = np.where(delta[..., 0] == 0)[0]
        if perp_indices.size > 0:
            delta[perp_indices, 0] = 1  # dx
            delta[perp_indices, 1] = np.inf * (
                    delta[perp_indices, 1] / np.abs(delta[perp_indices, 1])
            )  # dy
        ray_angles = np.arctan(delta[..., 1] / delta[..., 0])
        sort_i = np.argsort(ray_angles)
        corner_rays = corner_rays[sort_i]
        edge_points = edge_points[sort_i]

        # compute vectors corresponding to the mask edges
        edge_vectors = edge_pool[..., 1, :] - edge_pool[..., 0, :]

        # determine if a corner_ray intersects an edge that is closer
        # to the insertion point
        # - solving the eqn:
        #
        #   insertion_point + mu * corner_ray = edge_pool[..., 0, :] + nu * edge_vector
        #
        #   * mu and nu are scalars
        #   * if 0 < mu < 1 and 0 < nu < 1, then the corner_ray passes through a
        #     closer edge to the insertion point
        #
        mu_array = (
            np.cross(edge_pool[..., 0, :] - self.insertion_point, edge_vectors)
            / np.cross(corner_rays, edge_vectors[:, np.newaxis, ...]).swapaxes(0, 1)
        )
        nu_array = (
            np.cross(
                (self.insertion_point - edge_pool[..., 0, :])[:, np.newaxis, ...],
                corner_rays
            ).swapaxes(0, 1)
            / np.cross(edge_vectors[:, np.newaxis, ...], corner_rays).swapaxes(0, 1)
        )
        mu_condition = np.logical_and(mu_array > 0, mu_array < 1)
        nu_condition = np.logical_and(nu_array >= 0, nu_array < 1)
        intersection_mask = np.logical_and(mu_condition, nu_condition)

        # TODO: MUST PICK UP HERE

        # corner_rays = edge_pool.reshape(-1, 2) - self.insertion_point
        # corner_rays = self._shorten_rays_to_nearest_impact(corner_rays, edge_pool)

        return
