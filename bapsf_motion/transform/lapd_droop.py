__all__ = ["DroopCorrectABC", "LaPDXYDroopCorrect"]

import astropy.units as u

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
from warnings import warn

import numpy as np

from bapsf_motion.actors.drive_ import Drive


class DroopCorrectABC(ABC):
    _probe_shaft_od = NotImplemented  # type: u.Quantity
    _probe_shaft_wall = NotImplemented  # type: u.Quantity
    _probe_shaft_material = NotImplementedError  # type: str
    _dimensionality = NotImplemented  # type: int

    def __init__(self, drive: Drive, **kwargs):
        if isinstance(drive, Drive):
            self._drive = drive  # type: Union[Drive, None]
            self._axes = list(range(drive.naxes))
        elif (
                isinstance(drive, (list, tuple))
                and all(isinstance(dr, (int, str)) for dr in drive)
        ):
            # hidden mode for debugging purposes
            # - In this case drive is a list or tuple of int or str values
            #   that correspond to the axes' names.

            # TODO: ADD A WARNING HERE THAT WE ARE IN A DEBUG MODE

            self._drive = None
            self._axes = drive
        else:
            raise TypeError(
                f"For input argument 'drive' expected type {Drive}, but got type "
                f"{type(drive)}."
            )

        self.inputs = self._validate_inputs(kwargs)
        # self._config_keys = {"type"}.union(set(self.inputs.keys()))

        # self.dependencies = []  # type: List[BaseTransform]

        # validate matrix
        # self._validate_matrix_to_drive()
        # self._validate_matrix_to_motion_space()

    def __call__(self, points, to_points) -> np.ndarray:
        # validate to_coords
        valid_to_points = {"droop", "nondroop", "ndroop", "non-droop"}
        if not isinstance(to_points, str):
            raise TypeError(
                f"For argument 'to_points' expected type string, got type "
                f"{type(to_points)}."
            )
        elif to_points not in valid_to_points:
            raise ValueError(
                f"For argument 'to_points' expected a string value in "
                f"{valid_to_points}, but got {to_points}."
            )

        points = self._condition_points(points)
        adjusted_points = self._convert(points, to_points=to_points)

        return adjusted_points

    @property
    def axes(self):
        """A list of axis identifiers."""
        # TODO: this need to be redone to be more consistent with drive.axes
        return self._axes

    @property
    def naxes(self):
        """
        The number of axes of the probe drive.

        This is the same as the motion space dimensionality.
        """
        return len(self.axes)

    @property
    def dimensionality(self) -> int:
        """
        The designed dimensionality of the transform.  If ``-1``, then
        the transform does not have a fixed dimensionality, and it can
        morph to the associated |Drive|.
        """
        return self._dimensionality

    @property
    def drive(self) -> Union[Drive, None]:
        return self._drive

    @abstractmethod
    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate input arguments from class instantiation.

        Parameters
        ----------
        inputs: Dict[str, Any]
            The optional input arguments passed during class
            instantiation.
        """
        ...

    @abstractmethod
    def _convert_to_droop_points(self, points: np.ndarray) -> np.ndarray:
        ...

    @abstractmethod
    def _convert_to_nondroop_points(self, points: np.ndarray) -> np.ndarray:
        ...

    def _condition_points(self, points):
        # make sure points is a numpy array
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        # make sure points is always an N X M matrix
        if points.ndim == 1 and points.size == self.naxes:
            # single point was given
            points = points[np.newaxis, ...]
        elif points.ndim != 2:
            raise ValueError(
                f"Expected a 2D array of shape (N, {self.naxes}) for "
                f"'points', but got a {points.ndim}-D array."
            )
        elif self.naxes not in points.shape:
            raise ValueError(
                f"Expected a 2D array of shape (N, {self.naxes}) for "
                f"'points', but got shape {points.shape}."
            )
        elif points.shape[1] != self.naxes:
            # dimensions are flipped from expected
            points = np.swapaxes(points, 0, 1)

        return points

    def _convert(self, points, to_points):

        if to_points == "droop":
            adjusted_points = self._convert_to_droop_points(points)
        else:  # non-droop points
            adjusted_points = self._convert_to_nondroop_points(points)

        return adjusted_points


class LaPDXYDroopCorrect(DroopCorrectABC):
    _probe_shaft_od = 0.375 * u.imperial.inch
    _probe_shaft_wall = 0.035 * u.imperial.inch
    _probe_shaft_material = "Stainless Steel 304"
    _dimensionality = 2

    def __init__(self, drive: Drive, *, pivot_to_feedthru: float):
        super().__init__(
            drive=drive,
            pivot_to_feedthru=pivot_to_feedthru,
        )

        # this is the unit system used in generating the droop fit polynomial
        self._fit_units = u.cm  # type: u.Unit

        # Notes on the fit:
        #   - These fit coefficients were determined by running several FEA
        #     simulation in Solidworks on a stainless steel 304 tube of
        #     .375" OD x 0.035" wall
        #   - The simulation results were given in physical units of cm and,
        #     thus, the fit coefficients are in units of cm
        #   - The FEA held the probe shaft horizontal with the shaft extended
        #     a distance r from the fixed point and gravity is applied
        #     at an angle theta
        #
        #     fixed
        #          |<--       r      -->|
        #     -----|---------------------  <-
        #     -----|----____                |
        #                   ---___          ds
        #                         --__      |
        #                             -_    |
        #                               -  <-
        #    - the fit
        #        ds = (a3 * r**3 + a2 * r**2 + a1 * r + a0) r cos(theta)
        #
        # coeffs = [a0, a1, a2, a3]
        self._coeffs = np.array([6.209e-06, -2.211e-07, 2.084e-09, -5.491e-09])

    @property
    def pivot_to_feedthru(self):
        return self.inputs["pivot_to_feedthru"]

    @property
    def coefficients(self) -> np.ndarray:
        return self._coeffs

    def _convert_to_fit_units(self, points: np.ndarray) -> np.ndarray:
        # scale points from the deployed dive units to the units used
        # for determining the droop fit
        #
        if self._drive is None:
            return points

        drive_units = [ax.units for ax in self.drive.axes]  # type: List[u.Unit]
        if all(_u == self._fit_units for _u in drive_units):
            return points

        conversion_factor = [
            ((1 * _u).to(self._fit_units)).value
            for _u in drive_units
        ]
        return points[..., :] * conversion_factor[:]

    def _convert_to_deployed_units(self, points: np.ndarray) -> np.ndarray:
        # scale points from the units used for determining the droop fit
        # to the deployed dive units
        #
        if self._drive is None:
            return points

        drive_units = [ax.units for ax in self.drive.axes]
        if all(_u == self._fit_units for _u in drive_units):
            return points

        conversion_factor = [
            ((1 * self._fit_units).to(_u)).value
            for _u in drive_units
        ]
        return points[..., :] * conversion_factor[:]

    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        for key in {"pivot_to_feedthru"}:
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

        return inputs

    def _convert_to_droop_points(self, points: np.ndarray) -> np.ndarray:
        # points should be w.r.t. the ball valve and represent a non-droop
        # probe shaft
        #
        # convert points to the fit units
        _points = self._convert_to_fit_units(points)

        # Calculate radius and theta
        #    - rt => (radius, theta)
        points_rt = np.empty_like(points)
        points_rt[..., 0] = np.linalg.norm(_points, axis=1) + self.pivot_to_feedthru
        points_rt[..., 1] = np.tan(_points[..., 1] / _points[..., 0])

        # Calculate dx and dy of the droop
        #    - delta will always be negative in the ball valve coords
        #    - dx > 0 for theta > 0
        #    - dx = 0 for theta = 0
        #    - dx < 0 for theta < 0
        #    - dy < 0 always
        #
        # droop = (a3 * r**3 + a2 * r**2 + a1 * r + a0) * r cos(theta)
        #
        delta = (
            self.coefficients[3] * points_rt[..., 0] ** 3
            + self.coefficients[2] * points_rt[..., 0] ** 2
            + self.coefficients[1] * points_rt[..., 0]
            + self.coefficients[0]
        ) * points_rt[..., 0] * np.cos(points_rt[..., 1])
        dx = -delta[...] * np.sin(points_rt[..., 1])
        dy = delta[...] * np.cos(points_rt[..., 1])

        # Adjust to droop coords
        _points[..., 0] += dx
        _points[..., 1] += dy

        # 5. translate back to LaPD coords
        # droop_points[..., 0] = _sign * (self.pivot_to_center - droop_points[..., 0])

        return self._convert_to_deployed_units(_points)

    def _convert_to_nondroop_points(self, points: np.ndarray) -> np.ndarray:
        # there's no known solution in this direction, so we must iterate
        # - points is considered to be droop coords w.r.t to the Ball Valve

        ndroop_points = points.copy()
        test_points = self._convert_to_droop_points(ndroop_points)

        # Make an educated guess and iterate until we find the
        #    reasonable non-droop coords
        #
        # Notes for guessing:
        #      - non-droop y will always be higher than the droop y
        #      - non-droop x < droop x for theta > 0
        #      - non-droop x == droop x for theta = 0
        #      - non-droop x > droop x for theta < 0
        #
        i = 0
        while not np.allclose(test_points, points, rtol=0, atol=1e-8):
            i += 1
            ndroop_points[..., 0] += -1.5 * (test_points[..., 0] - points[..., 0])
            ndroop_points[..., 1] += -1.5 * (test_points[..., 1] - points[..., 1])

            test_points = self._convert_to_droop_points(ndroop_points)

            if i == 100:
                print(i)
                break

        return ndroop_points
