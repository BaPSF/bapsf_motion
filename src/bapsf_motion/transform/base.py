"""Module that defines the `BaseTransform` abstract class."""
__all__ = ["BaseTransform"]

import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union

from bapsf_motion.actors import Drive
from bapsf_motion.motion_list import MotionList


class BaseTransform(ABC):
    """
    Abstract base class for coordinate transform classes.

    Parameters
    ----------
    drive: |Drive|
        The instance of |Drive| the coordinate transformer will be
        working with.

    kwargs: Dict[str, Any]
        Keyword arguments that are specific to the subclass.
    """
    _transform_type = NotImplemented  # type: str

    # TODO: add method illustrate_transform() to plot and show how the
    #       space in transformed

    def __init__(self, drive: Drive, **kwargs):

        if isinstance(drive, Drive):
            self._drive = drive
            self._axes = list(range(drive.naxes))
        elif isinstance(drive, (list, tuple)) and all(isinstance(dr, (int, str)) for dr in drive):
            # hidden mode for debugging purposes

            # TODO: ADD A WARNING HERE THAT WE ARE IN A DEBUG MODE

            self._drive = None
            self._axes = drive
        else:
            raise TypeError(
                f"For input argument 'drive' expected type {Drive}, but got type "
                f"{type(drive)}."
            )

        self.inputs = self._validate_inputs(kwargs)
        self._config_keys = {"type"}.union(set(self.inputs.keys()))

        self.dependencies = []  # type: List[BaseTransform]

        # validate matrix
        matrix = self._matrix([0.0] * len(self.axes))
        if not isinstance(matrix, np.ndarray):
            raise TypeError
        elif matrix.shape != tuple(2 * [len(self.axes) + 1]):
            # matrix needs to be square with each dimension being one size
            # larger than the number axes the matrix transforms...the last
            # dimensions allows for shift translations
            raise ValueError(f"matrix.shape = {matrix.shape}")

    def __call__(self, points, to_coords="drive"):
        return self._convert(points, to_coords=to_coords)

    @property
    def axes(self):
        return self._axes

    @property
    def transform_type(self) -> str:
        """
        String naming the coordinate transformation type.  This is
        unique among all subclasses of `BaseTransform`."""
        return self._transform_type

    @property
    def config(self) -> Dict[str, Any]:
        """
        A dictionary containing the coordinate transformation
        configuration.
        """
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.transform_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

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

    def _matrix(self, points, to_coords="drive") -> np.ndarray:
        r"""
        The transformation matrix used to transform from probe drive
        coordinates to motion space coordinates, and vice versa.

        Parameters
        ----------
        points: :term:`array_like`
            A single point or array of points for which the
            transformation will be generated.  The array of points
            needs to be of size :math:`M` or :math:`M \times N` where
            :math:`M` is the dimensionality of the :term:`motion space`
            and :math:`N` is the number of points to be transformed.

        to_coords: `str`
            If ``"drive"``, then generate a transformation matrix that
            converts :term:`motion space` coordinates to probe drive
            coordinates.  If ``"motion space"``, then generate a
            transformation matrix that converts probe drive
            coordinates to :term:`motion space` coordinates.
            (DEFAULT: ``"drive"``)

        Returns
        -------
        matrix: :term:`array_like`
            A transformation matrix of size
            :math:`M+1 \times M+1 \times N`.  The :math:`M+1`
            dimensionality allows for the inclusion of a dimension
            for coordinate translations.

        Notes
        -----

        The generated matrix must have a dimensionality of
        :math:`M+1 \times M+1 \times N` where :math:`M` is the
        dimensionality of the :term:`motion space` and
        :math:`N` is the number of points passed in.  The +1 in the
        transformation matrix dimensionality corresponds to a dimension
        that allows for translational shifts in the coordinate
        transformation.  For example, if a 2D probe drive is being used
        then the generated matrix for a single point would have a size
        of :math:`3 \times 3 \times 1`.

        The matrix generation takes a ``points`` argument because not
        all transformations are agnostic of the starting location, for
        example, the XY :term:`LaPD` :term:`probe drive`.
        """
        # to_coord should have two options "drive" and "motion_space"
        # - to_coord="drive" means to convert from motion space coordinates
        #   to drive coordinates
        # - to_coord="motion_space" converts in the opposite direction as
        #   to_coord="drive"
        #
        # TODO: would to_coord be better as a to_drive that has a boolean value
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        if to_coords == "drive":
            return self._matrix_to_drive(points)
        elif to_coords in ("mspace", "motion_space", "motion space"):
            return self._matrix_to_motion_space(points)
        else:
            raise ValueError(
                f"Keyword 'to_coords' can only have values 'drive' or "
                f"'motion_space', but got '{to_coords}'."
            )

    def _convert(self, points, to_coords="drive"):
        # TODO: this convert function still need to be test to show
        #       that it'll work for N-dimensions...I stole this from
        #       LaPDXYTransform.convert() so it works in a world where
        #       the generated matrix _matrix() is 3x3 but the points/positions
        #       are only given as a 2-element vector

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
        return np.einsum("kmn,kn->km", matrix, points)[..., :-1]

    @abstractmethod
    def _matrix_to_drive(self, points):
        ...

    @abstractmethod
    def _matrix_to_motion_space(self, points):
        ...


class _Base2Transform(ABC):
    """
    This was a first attempt at a BaseTransform class.  I'm keeping it
    around until I'm satisfied with BaseTransform or reimplement all
    of _Base2Transform into BaseTransform.
    """
    _transform_type = NotImplemented  # type: str

    # TODO: Possible useful methods
    #       - time to move to point (from current position)
    #       - equalize move movement to next point (est. speed, accel,
    #         and decel so all drive axes finish movement at the same
    #         time)
    #       - est. time to complete motion list (this might be more
    #         suited on the MotionGroup class, or MotionList class)

    def __init__(
        self,
        drive: Drive,
        # *,
        # ml: MotionList = None,
        **kwargs,
    ):
        self._drive = self._validate_drive(drive)
        # self._ml = self._validate_motion_list(ml)

        self.inputs = self._validate_inputs(kwargs)
        self._config_keys = {"type"}.union(set(self.inputs.keys()))

        self.dependencies = []  # type: List[BaseTransform]

    @property
    def transform_type(self):
        return self._transform_type

    @property
    def config(self):
        config = {}
        for key in self._config_keys:
            if key == "type":
                config[key] = self.transform_type
            else:
                val = self.inputs[key]
                if isinstance(val, np.ndarray):
                    val = val.tolist()
                config[key] = val if not isinstance(val, np.generic) else val.item()
        return config

    @property
    def drive(self):
        return self._drive

    # @property
    # def ml(self):
    #     return self._ml

    @staticmethod
    def _validate_drive(drive: "Drive") -> "Drive":
        if not isinstance(drive, Drive):
            raise TypeError(
                f"Argument 'drive' expected type "
                f"{Drive.__module__}.{Drive.__qualname__} and got type "
                f"{type(drive)}."
            )

        return drive

    def _validate_motion_list(self, ml: Optional[MotionList]) -> Optional[MotionList]:
        if ml is None:
            return
        elif not isinstance(ml, MotionList):
            raise TypeError(
                f"Argument 'ml' expected type "
                f"{MotionList.__module__}.{MotionList.__qualname__}, and "
                f"got type {type(ml)}."
            )
        elif self.drive.naxes != ml.mspace_ndims:
            raise ValueError(
                f"The given 'drive' object and motion list 'ml' object "
                f" do not have matching dimensions, got "
                f"{self.drive.naxes} and {ml.mspace_ndims} respectively."
            )
        elif set(self.drive.anames) != set(ml.mspace_coords.dims):
            raise ValueError(
                f"The give 'drive' axis names and motion spaces axis "
                f"names do not match, got {set(self.drive.anames)} and "
                f"{set(ml.mspace_coords.dims)} respectively."
            )

        return ml

    @abstractmethod
    def _validate_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def convert(self, points, to_coord="drive"):
        # to_coord should have two options "drive" and "motion_space"
        # - to_coord="drive" means to convert from motion space coordinates
        #   to drive coordinates
        # - to_coord="motion_space" converts in the opposite direction as
        #   to_coord="drive"
        #
        # TODO: would to_coord be better as a to_drive that has a boolean value
        ...
