"""
Module that defines the `LaPDXYExclusion` class.
"""
__all__ = ["LaPDXYExclusion"]
__mexclusions__ = ["LaPDXYExclusion"]

import numpy as np
import xarray as xr

from numbers import Real
from typing import Union

from bapsf_motion.motion_builder.exclusions.base import BaseExclusion
from bapsf_motion.motion_builder.exclusions.circular import CircularExclusion
from bapsf_motion.motion_builder.exclusions.divider import DividerExclusion
from bapsf_motion.motion_builder.exclusions.helpers import register_exclusion


@register_exclusion
class LaPDXYExclusion(BaseExclusion):
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
        bottom\ :math:`\}` (case insensitive) or an angle
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
        diameter: Real = 100,
        pivot_radius: Real = 58.771,
        port_location: Union[str, Real] = "E",
        cone_full_angle: Real = 80,
        include_cone: bool = True,
    ):
        super().__init__(
            ds,
            diameter=diameter,
            pivot_radius=pivot_radius,
            port_location=port_location,
            cone_full_angle=cone_full_angle,
            include_cone=include_cone,
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

    def _combine_exclusions(self):
        """Combine all sub-exclusions into one exclusion array."""
        exclusion = None
        for ex in self.composed_exclusions:
            if exclusion is None:
                exclusion = ex.exclusion
            else:
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
        self.composed_exclusions.append(
            CircularExclusion(
                self._ds,
                skip_ds_add=True,
                radius=0.5 * self.diameter,
                center=(0.0, 0.0),
                exclude="outside",
            )
        )

        if not self.include_cone:
            return self._combine_exclusions()

        # determine slope for code exclusion
        # - P is considered a point in the LaPD coordinate system
        # - P' is considered a point in the pivot (port) coordinate system
        theta = np.radians(self.port_location)
        alpha = 0.5 * np.radians(self.cone_full_angle)
        pivot_xy = np.array(
            [
                self.pivot_radius * np.cos(theta),
                self.pivot_radius * np.sin(theta),
            ],
        )

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

            self.composed_exclusions.append(
                DividerExclusion(
                    self._ds,
                    skip_ds_add=True,
                    mb=(slope, intercept),
                    exclude=exclude,
                )
            )

        return self._combine_exclusions()
