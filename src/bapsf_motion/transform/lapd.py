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
    ):
        super().__init__(
            drive,
            pivot_to_center=pivot_to_center,
            pivot_to_drive=pivot_to_drive,
            probe_axis_offset=probe_axis_offset,
            drive_polarity=drive_polarity,
            mspace_polarity=mspace_polarity,
        )

        # naxes = len(self.axes) if self._drive is None else self._drive.naxes
        #
        # if naxes != 2:
        #     raise ValueError(
        #         f"The LaPDXYTransform requires two axes to operate on, the "
        #         f"specified probe drive has {drive.naxes} axes."
        #     )

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:

        for key in {"pivot_to_center", "pivot_to_drive", "probe_axis_offset"}:
            val = inputs[key]
            if not isinstance(val, (float, np.floating, int, np.integer)):
                raise TypeError(
                    f"Keyword '{key}' expected type float or int, "
                    f"got type {type(val)}."
                )
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

        return inputs

    def _matrix(self, points, to_coords="drive") -> np.ndarray:
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        points = points.squeeze()
        if points.ndim not in (1, 2):
            raise ValueError(
                f"Expected given 'points' to ndims 1 or 2, got {points.ndim}."
            )
        elif points.ndim == 1 and points.size != 2:
            # a single point must have both x and y values
            raise ValueError
        elif points.ndim == 2 and points.shape[1] != 2:
            # if an array of points is given then the second dimension
            # must give x and y values
            raise ValueError

        return super()._matrix(points, to_coords=to_coords)

    def _matrix_to_motion_space(self, points: np.ndarray):
        # given points are in drive (e0, e1) coordinates

        # polarity needs to be adjusted first, since the parameters for
        # the following transformation matrices depend on the adjusted
        # coordinate space
        points = self.drive_polarity * points  # type: np.ndarray
        points[..., 1] = points[..., 1] - self.probe_axis_offset

        gamma = np.arctan(points[..., 1] / self.pivot_to_drive)
        beta = np.arcsin(
            self.probe_axis_offset / np.sqrt(
                self.pivot_to_drive**2 + points[..., 1]**2
            )
        )
        theta = gamma + beta
        alpha = np.pi - theta

        # theta = np.arctan(points[..., 1] / self.pivot_to_drive)
        # alpha = np.pi - theta

        npoints = 1 if points.ndim == 1 else points.shape[0]

        # handle the probe axis to drive axis parallel offset
        T0 = np.zeros((npoints, 3, 3)).squeeze()
        T0[..., 0, 0] = 1.0
        # T0[..., 0, 2] = -self.probe_axis_offset * np.tan(theta)
        T0[..., 1, 1] = 1.0
        T0[..., 1, 2] = self.probe_axis_offset * ((1 / np.cos(theta)) - 1)
        T0[..., 2, 2] = 1.0

        # transform drive axes to drive side pivot coords
        T1 = np.zeros((npoints, 3, 3)).squeeze()
        T1[..., 0, 0] = np.cos(theta)
        T1[..., 0, 2] = -self.pivot_to_drive * np.cos(theta)
        T1[..., 1, 0] = -np.sin(theta)
        T1[..., 1, 2] = self.pivot_to_drive * np.sin(theta)
        T1[..., 2, 2] = 1.0

        # transform drive side pivot coords to motion space side pivot coords
        T2 = np.zeros((npoints, 3, 3)).squeeze()
        T2[..., 0, 0] = 1.0
        T2[..., 0, 2] = -(self.pivot_to_drive + self.pivot_to_center) * np.cos(alpha)
        T2[..., 1, 1] = 1.0
        T2[..., 1, 2] = -(self.pivot_to_drive + self.pivot_to_center) * np.sin(alpha)
        T2[..., 2, 2] = 1.0

        # transform motion space side pivot coords to motion space coords
        T3 = np.zeros((npoints, 3, 3)).squeeze()
        T3[..., 0, 0] = 1.0
        T3[..., 0, 2] = -self.pivot_to_center
        T3[..., 1, 1] = 1.0
        T3[..., 2, 2] = 1.0

        T_dpolarity = np.diag(self.drive_polarity.tolist() + [1.0])
        T_mpolarity = np.diag(self.mspace_polarity.tolist() + [1.0])

        # return np.matmul(
        #     T_mpolarity,
        #     np.matmul(
        #         T3,
        #         np.matmul(
        #             T2,
        #             np.matmul(T1, T_dpolarity),
        #         ),
        #     ),
        # )
        return np.matmul(
            T_mpolarity,
            np.matmul(
                T3,
                np.matmul(
                    T2,
                    np.matmul(
                        T1,
                        np.matmul(T0, T_dpolarity),
                    ),
                ),
            ),
        )

    def _matrix_to_drive(self, points):
        # given points are in motion space "LaPD" (x, y) coordinates

        # polarity needs to be adjusted first, since the parameters for
        # the following transformation matrices depend on the adjusted
        # coordinate space
        points = self.mspace_polarity * points  # type: np.ndarray

        # need to handle when x_L = pivot_to_center
        # since alpha can never be 90deg we don't need to worry about that case
        alpha = np.arctan(points[..., 1] / (self.pivot_to_center + points[..., 0]))

        npoints = 1 if points.ndim == 1 else points.shape[0]

        # transform motion space coords to motion space side pivot coords
        T1 = np.zeros((npoints, 3, 3)).squeeze()
        T1[..., 0, 0] = 1.0
        T1[..., 0, 2] = self.pivot_to_center
        T1[..., 1, 1] = 1.0
        T1[..., 2, 2] = 1.0

        # transform motion space side pivot coords to drive side pivot coords
        T2 = np.zeros((npoints, 3, 3)).squeeze()
        T2[..., 0, 0] = 1.0
        T2[..., 0, 2] = -(self.pivot_to_drive + self.pivot_to_center) * np.cos(alpha)
        T2[..., 1, 1] = 1.0
        T2[..., 1, 2] = -(self.pivot_to_drive + self.pivot_to_center) * np.sin(alpha)
        T2[..., 2, 2] = 1.0

        # transform drive side pivot coords to drive axes
        T3 = np.zeros((npoints, 3, 3)).squeeze()
        T3[..., 0, 0] = 1 / np.cos(alpha)
        T3[..., 0, 2] = self.pivot_to_drive
        T3[..., 1, 2] = -self.pivot_to_drive * np.tan(alpha)
        T3[..., 2, 2] = 1.0

        # handle the probe axis to drive axis parallel offset
        T4 = np.zeros((npoints, 3, 3)).squeeze()
        T4[..., 0, 0] = 1.0
        # T4[..., 0, 2] = self.probe_axis_offset * np.tan(-alpha)
        T4[..., 1, 1] = 1.0
        T4[..., 1, 2] = -self.probe_axis_offset * ((1 / np.cos(-alpha)) - 1)
        T4[..., 2, 2] = 1.0

        T_dpolarity = np.diag(self.drive_polarity.tolist() + [1.0])
        T_mpolarity = np.diag(self.mspace_polarity.tolist() + [1.0])

        # return np.matmul(
        #     T_dpolarity,
        #     np.matmul(
        #         T3,
        #         np.matmul(
        #             T2,
        #             np.matmul(T1, T_mpolarity),
        #         ),
        #     ),
        # )
        return np.matmul(
            T_dpolarity,
            np.matmul(
                T4,
                np.matmul(
                    T3,
                    np.matmul(
                        T2,
                        np.matmul(T1, T_mpolarity),
                    ),
                ),
            ),
        )

    def _convert(self, points, to_coords="drive"):
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        matrix = self._matrix(points, to_coords=to_coords)

        if points.ndim == 1:
            points = np.concatenate((points, [1]))
            return np.matmul(matrix, points)[:2]

        points = np.concatenate(
            (points, np.ones((points.shape[0], 1))),
            axis=1,
        )
        return np.einsum("kmn,kn->km", matrix, points)[..., :2]

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
