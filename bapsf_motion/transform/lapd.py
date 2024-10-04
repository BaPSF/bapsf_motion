"""Module that defines the `LaPDXYTransform` abstract class."""
__all__ = ["LaPDXYTransform"]
__transformer__ = ["LaPDXYTransform"]

import numpy as np

from typing import Any, Dict, Tuple
from warnings import warn

from bapsf_motion.transform import base
from bapsf_motion.transform.helpers import register_transform


@register_transform
class LaPDXYTransform(base.BaseTransform):
    """
    Class that defines a coordinate transform for a :term:`LaPD` XY
    :term:`probe drive`.

    **transform type:** ``'lapd_xy'``

    Parameters
    ----------
    drive: |Drive|
        The instance of |Drive| the coordinate transformer will be
        working with.

    pivot_to_center: `float`
        Distance from the center of the :term:`LaPD` to the center
        "pivot" point of the ball valve.

    pivot_to_drive: `float`
        Distance from the center line of the :term:`probe drive`
        vertical axis to the center "pivot" point of the ball valve.

    probe_axis_offset: `float`
        Perpendicular distance from the center line of the probe shaft
        to the :term:`probe drive` pivot point on the vertical axis.

    drive_polarity: 2D tuple, optional
        A two element tuple of +/- 1 values indicating the polarity of
        the probe drive motion to how the math was done for the
        underlying matrix transformations.  For example, a value
        of ``(1, 1)`` would indicate that positive movement (in
        probe drive coordinates) of the drive would be inwards and
        downwards.  However, this is inconsistent if the vertical axis
        has the motor mounted to the bottom of the axis.  In this case
        the ``drive_polarity`` would be ``(1, -1)``.
        (DEFAULT: ``(1, 1)``)

    mspace_polarity: 2D tuple, optional
        A two element tuple of +/- 1 values indicating the polarity of
        the motion space motion to how the math was done for the
        underlying matrix transformations.  For example, a value
        of ``(-1, 1)`` for a probe mounted on an East port would
        indicate that inward probe drive movement would correspond to
        a LaPD -X movement and downward probe drive movement
        would correspond to LaPD +Y.  If the probe was mounted on a
        West port then the polarity would need to be ``(1, 1)`` since
        inward probe drive movement corresponds to +X LaPD coordinate
        movement.  (DEFAULT: ``(-1, 1)``)

    Examples
    --------

    Let's set up a :term:`transformer` for a probe drive mounted on
    an east port.  In this case the vertical axis motor is mounted
    at the top of the vertical axis.  (Values are NOT accurate to
    actual LaPD values.)

    .. tabs::
       .. code-tab:: py Class Instantiation

          tr = LaPDXYTransform(
              drive,
              pivot_to_center = 62.94,
              pivot_to_drive = 133.51,
              probe_axis_offset = 20.16,
              drive_polarity = (1, 1),
              mspace_polarity = (-1, 1),
          )

       .. code-tab:: py Factory Function

          tr = transform_factory(
              drive,
              tr_type = "lapd_xy",
              **{
                  "pivot_to_center": 62.94,
                  "pivot_to_drive": 133.51,
                  "probe_axis_offset": 20.16,
                  "drive_polarity": (1, 1),
                  "mspace_polarity": (-1, 1),
              },
          )

       .. code-tab:: toml TOML

          [...transform]
          type = "lapd_xy"
          pivot_to_center = 62.94
          pivot_to_drive = 133.51
          probe_axis_offset = 20.16
          drive_polarity = (1, 1)
          mspace_polarity = (-1, 1)

       .. code-tab:: py Dict Entry

          config["transform"] = {
              "type": "lapd_xy",
              "pivot_to_center": 62.94,
              "pivot_to_drive": 133.51,
              "probe_axis_offset": 20.16,
              "drive_polarity": (1, 1),
              "mspace_polarity": (-1, 1),
          }

    Now, let's do the same thing for a probe drive mounted on a West
    port and has the vertical axis motor mounted at the base.

    .. tabs::
       .. code-tab:: py Class Instantiation

          tr = LaPDXYTransform(
              drive,
              pivot_to_center = 62.94,
              pivot_to_drive = 133.51,
              probe_axis_offset = 20.16,
              drive_polarity = (1, -1),
              mspace_polarity = (1, 1),
          )

       .. code-tab:: py Factory Function

          tr = transform_factory(
              drive,
              tr_type = "lapd_xy",
              **{
                  "pivot_to_center": 62.94,
                  "pivot_to_drive": 133.51,
                  "probe_axis_offset": 20.16,
                  "drive_polarity": (1, -1),
                  "mspace_polarity": (1, 1),
              },
          )

       .. code-tab:: toml TOML

          [...transform]
          type = "lapd_xy"
          pivot_to_center = 62.94
          pivot_to_drive = 133.51
          probe_axis_offset = 20.16
          drive_polarity = (1, -1)
          mspace_polarity = (1, 1)

       .. code-tab:: py Dict Entry

          config["transform"] = {
              "type": "lapd_xy",
              "pivot_to_center": 62.94,
              "pivot_to_drive": 133.51,
              "probe_axis_offset": 20.16,
              "drive_polarity": (1, -1),
              "mspace_polarity": (1, 1),
          }
    """
    # TODO: confirm polarity descriptions once issue #38 is resolved
    # TODO: review that default polarities are correct
    # TODO: write a full primer on how the coordinate transform was
    #       calculated
    _transform_type = "lapd_xy"
    _dimensionality = 2

    def __init__(
        self,
        drive,
        *,
        pivot_to_center: float,
        pivot_to_drive: float,
        probe_axis_offset: float,
        drive_polarity: Tuple[int, int] = (1, 1),
        mspace_polarity: Tuple[int, int] = (-1, 1),
        droop_correct: bool = False,
    ):
        super().__init__(
            drive,
            pivot_to_center=pivot_to_center,
            pivot_to_drive=pivot_to_drive,
            probe_axis_offset=probe_axis_offset,
            drive_polarity=drive_polarity,
            mspace_polarity=mspace_polarity,
            droop_correct=droop_correct,
            deployed_side="East",
        )

    def __call__(self, points, to_coords="drive") -> np.ndarray:
        if not self.droop_correct:
            return super().__call__(points=points, to_coords=to_coords)

        if to_coords == "drive":
            # need to convert motion space coordinates to non-droop
            # scenario before doing matrix multiplication
            points = self._condition_points(points)
            
        else:  # to motion space
            tr_points = super().__call__(points=points, to_coords=to_coords)
            tr_points = self._droop_correct_to_motion_space(tr_points)

        return tr_points

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:

        for key in {"pivot_to_center", "pivot_to_drive", "probe_axis_offset"}:
            val = inputs[key]
            if not isinstance(val, (float, np.floating, int, np.integer)):
                raise TypeError(
                    f"Keyword '{key}' expected type float or int, "
                    f"got type {type(val)}."
                )
            elif key == "pivot_to_center":
                inputs["deployed_side"] = "East" if val >= 0.0 else "West"
                inputs["pivot_to_center"] = np.abs(val)
            elif val < 0.0:
                # TODO: HOW (AND SHOULD WE) ALLOW A NEGATIVE OFFSET FOR
                #       "probe_axis_offset"
                val = np.abs(val)
                warn(
                    f"Keyword '{val}' is NOT supposed to be negative, "
                    f"assuming the absolute value {val}."
                )
            inputs[key] = val

        for key in ("drive_polarity", "mspace_polarity"):
            polarity = inputs[key]
            if not isinstance(polarity, np.ndarray):
                polarity = np.array(polarity)

            if polarity.shape != (2,):
                raise ValueError(
                    f"Keyword '{key}' is supposed to be a 2-element "
                    "array specifying the polarity of the axes, got "
                    f"an array of shape {polarity.shape}."
                )
            elif not np.all(np.abs(polarity) == 1):
                raise ValueError(
                    f"Keyword '{key}' is supposed to be a 2-element "
                    "array of 1 or -1 specifying the polarity of the "
                    "axes, array has values not equal to 1 or -1."
                )
            inputs[key] = polarity

        if not isinstance(inputs["droop_correct"], bool):
            raise TypeError(
                f"Keyword 'droop_correct' expected type bool, "
                f"got type {type(inputs['droop_correct'])}."
            )

        return inputs

    def _matrix_to_drive(self, points):
        # given points are in motion space "LaPD" (x, y) coordinates

        # polarity needs to be adjusted first, since the parameters for
        # the following transformation matrices depend on the adjusted
        # coordinate space
        points = self.mspace_polarity * points  # type: np.ndarray
        npoints = points.shape[0]

        tan_theta = points[..., 1] / (points[..., 0] + self.pivot_to_center)
        theta = -np.arctan(tan_theta)

        T0 = np.zeros((npoints, 3, 3)).squeeze()
        T0[..., 0, 2] = np.sqrt(
            points[..., 1]**2 + (self.pivot_to_center + points[..., 0])**2
        ) - self.pivot_to_center
        T0[..., 1, 2] = (
            self.pivot_to_drive * np.tan(theta)
            + self.probe_axis_offset * (1 - (1 / np.cos(theta)))
        )
        T0[..., 2, 2] = 1.0

        T_dpolarity = np.diag(self.drive_polarity.tolist() + [1.0])
        T_mpolarity = np.diag(self.mspace_polarity.tolist() + [1.0])

        return np.matmul(
            T_dpolarity,
            np.matmul(T0, T_mpolarity),
        )

    def _matrix_to_motion_space(self, points: np.ndarray):
        # given points are in drive (e0, e1) coordinates

        # polarity needs to be adjusted first, since the parameters for
        # the following transformation matrices depend on the adjusted
        # coordinate space
        points = self.drive_polarity * points  # type: np.ndarray
        npoints = points.shape[0]

        # Angle Defs:
        # - theta = angle between the horizontal and the probe shaft
        # - beta = angle between the horizontal and the probe drive pivot
        #          point on e1 (the vertical axis)
        # - alpha = beta - theta

        sine_alpha = self.probe_axis_offset / np.sqrt(
            self.pivot_to_drive**2
            + (-self.probe_axis_offset + points[..., 1])**2
        )

        tan_beta = (-self.probe_axis_offset + points[..., 1]) / -self.pivot_to_drive

        # alpha = arcsine( sine_alpha )
        # beta = pi + arctan( tan_beta )
        # theta = beta - alpha
        # theta2 = theta - pi

        theta = np.arctan(tan_beta) - np.arcsin(sine_alpha)

        T0 = np.zeros((npoints, 3, 3)).squeeze()
        T0[..., 0, 0] = np.cos(theta)
        T0[..., 0, 2] = -self.pivot_to_center * (1 - np.cos(theta))
        T0[..., 1, 0] = np.sin(theta)
        T0[..., 1, 2] = self.pivot_to_center * np.sin(theta)
        T0[..., 2, 2] = 1.0

        T_dpolarity = np.diag(self.drive_polarity.tolist() + [1.0])
        T_mpolarity = np.diag(self.mspace_polarity.tolist() + [1.0])

        return np.matmul(
            T_mpolarity,
            np.matmul(T0, T_dpolarity),
        )

    def _droop_correct_to_motion_space(self, points: np.ndarray):
        # droop = (a3 * r**3 + a2 * r**2 + a1 * r + a0) * r cos(theta)
        #
        # - points should be in non-drooped LaPD coordinates
        # - coeffs = [a0, a1, a2, a3]
        # - these coefficients are for a coordinate system using
        #   physical units of cm
        #
        coeffs = [6.209e-06, -2.211e-07, 2.084e-09, -5.491e-09]
        droop_points = np.zeros_like(points)

        # 1. backtrack coordinates to the ball valve pivot
        #    - Ball Valve Y -> LaPD Y
        #    - Ball Valve X -> | pivot_to_center - LaPD X |
        _sign = 1 if self.deployed_side == "East" else -1
        droop_points[..., 0] = np.absolute(_sign * self.pivot_to_center - points[..., 0])
        droop_points[..., 1] = points[..., 1]

        # 2. calculate r and theta (w.r.t. the ball valve)
        #    - rt => (radius, theta)
        points_rt = np.empty_like(points)
        points_rt[..., 0] = np.linalg.norm(droop_points, axis=1)
        points_rt[..., 1] = np.tan(droop_points[..., 1] / droop_points[..., 0])

        # 3. calculate dx and dy of the droop
        #    - delta will always be negative in the ball valve coords
        #    - dx > 0 for theta > 0
        #    - dx = 0 for theta = 0
        #    - dx < 0 for theta < 0
        #    - dy < 0 always
        #
        delta = (
            coeffs[3] * droop_points[..., 0]**3
            + coeffs[2] * droop_points[..., 0]**2
            + coeffs[1] * droop_points[..., 0]
            + coeffs[0]
        ) * droop_points[..., 0]
        dx = -delta[...] * np.sin(points_rt[..., 1])
        dy = delta[...] * np.cos(points_rt[..., 1])

        # 4. "correct" to droop coords
        droop_points[..., 0] += dx
        droop_points[..., 1] += dy

        # 5. translate back to LaPD coords
        droop_points[..., 0] = _sign * (self.pivot_to_center - droop_points[..., 0])

        return droop_points

    @property
    def pivot_to_center(self) -> float:
        """
        Distance from the center of the :term:`LaPD` to the center
        "pivot" point of the ball valve.
        """
        return self.inputs["pivot_to_center"]

    @property
    def pivot_to_drive(self) -> float:
        """
        Distance from the center line of the :term:`probe drive`
        vertical axis to the center "pivot" point of the ball valve.
        """
        return self.inputs["pivot_to_drive"]

    @property
    def probe_axis_offset(self) -> float:
        """
        Perpendicular distance from the center line of the probe shaft
        to the :term:`probe drive` pivot point on the vertical axis.
        """
        return self.inputs["probe_axis_offset"]

    @property
    def drive_polarity(self) -> np.ndarray:
        """
        A two element array of +/- 1 values indicating the polarity of
        the probe drive motion to how the math was done for the
        underlying matrix transformations.

        For example, a value of ``[1, 1]`` would indicate that positive
        movement (in probe drive coordinates) of the drive would be
        inwards and downwards.  However, this is inconsistent if the
        vertical axis has the motor mounted to the bottom of the axis.
        In this case the ``drive_polarity`` would be ``(1, -1)``.
        """
        return self.inputs["drive_polarity"]

    @property
    def mspace_polarity(self) -> np.ndarray:
        """
        A two element array of +/- 1 values indicating the polarity of
        the motion space motion to how the math was done for the
        underlying matrix transformations.

        For example, a value of ``(-1, 1)`` for a probe mounted on an
        East port would indicate that inward probe drive movement would
        correspond to a LaPD -X movement and downward probe drive
        movement would correspond to LaPD +Y.  If the probe was mounted
        on a West port then the polarity would need to be ``(1, 1)``
        since inward probe drive movement corresponds to +X LaPD
        coordinate movement.
        """
        return self.inputs["mspace_polarity"]

    @property
    def droop_correct(self) -> bool:
        return self.inputs["droop_correct"]

    @property
    def deployed_side(self):
        return self.inputs["deployed_side"]
