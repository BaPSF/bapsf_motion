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
from bapsf_motion.motion_builder.exclusions.shadow import Shadow2DExclusion


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
        # pre-define attributes that will be fully defined by self._validate_inputs()
        self._insertion_point = None

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
        return self._insertion_point

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

        # populate additional attributes
        self._insertion_point = np.array(
            [
                self.pivot_radius * np.cos(np.deg2rad(self.port_location)),
                self.pivot_radius * np.sin(np.deg2rad(self.port_location)),
            ],
        )

    def _combine_exclusions(self):
        """Combine all sub-exclusions into one exclusion array."""
        ex1 = self.composed_exclusions["chamber"]
        try:
            ex2 = self.composed_exclusions["port"]
            exclusion = np.logical_or(ex1.exclusion, ex2.exclusion)
        except KeyError:
            exclusion = ex1.exclusion
            pass

        for ex_name, ex in self.composed_exclusions.items():
            if ex_name in {"chamber", "port"}:
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
        ex = self._generate_shadow_exclusion()
        self.composed_exclusions["shadow"] = ex

        ex = self._generate_chamber_exclusion()
        self.composed_exclusions["chamber"] = ex

        if not self.include_cone:
            return self._combine_exclusions()

        ex = self._generate_port_exclusion()
        self.composed_exclusions["port"] = ex

        exs = self._generate_cone_exclusions()
        self.composed_exclusions.update(exs)

        return self._combine_exclusions()

    def _generate_chamber_exclusion(self):
        ex = CircularExclusion(
            self._ds,
            skip_ds_add=True,
            radius=0.5 * self.diameter,
            center=(0.0, 0.0),
            exclude="outside",
        )
        return ex

    def _generate_cone_exclusions(self):
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
        exclusions = {}
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
            exclusions[f"divider_{key}"] = ex

        return exclusions

    def _generate_port_exclusion(self):
        # divider representing the port opening
        theta = np.radians(self.port_location)
        alpha = 0.5 * np.radians(self.cone_full_angle)
        pivot_xy = self.insertion_point

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
        return ex

    def _generate_shadow_exclusion(self):
        ex = Shadow2DExclusion(
            self._ds,
            skip_ds_add=True,
            source_point=self.insertion_point,
        )
        return ex
