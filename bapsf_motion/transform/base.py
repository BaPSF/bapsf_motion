"""Module that defines the `BaseTransform` abstract class."""
__all__ = ["BaseTransform"]

import numpy as np

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from bapsf_motion.actors.drive_ import Drive


class BaseTransform(ABC):
    """
    Abstract base class for coordinate transform classes.

    Parameters
    ----------
    drive: |Drive|
        The instance of |Drive| the coordinate transformer will be
        working with.

    kwargs:
        Keyword arguments that are specific to the subclass.
    """
    _transform_type = NotImplemented  # type: str
    _dimensionality = NotImplemented  # type: int

    # TODO: add method illustrate_transform() to plot and show how the
    #       space in transformed

    def __init__(self, drive: Drive, **kwargs):

        if isinstance(drive, Drive):
            self._drive = drive
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
        self._config_keys = {"type"}.union(set(self.inputs.keys()))

        self.dependencies = []  # type: List[BaseTransform]

        # validate matrix
        matrix = self._matrix(
            np.array([0.0] * len(self._axes))[..., np.newaxis]
        )
        if not isinstance(matrix, np.ndarray):
            raise TypeError
        elif matrix.shape != tuple(2 * [len(self._axes) + 1]) + (1,):
            # matrix needs to be square with each dimension being one size
            # larger than the number axes the matrix transforms...the last
            # dimensions allows for shift translations
            raise ValueError(f"matrix.shape = {matrix.shape}")
        elif self._dimensionality > 0 and self._dimensionality != len(self._axes):
            raise ValueError(
                f"The transform was design for probe drives with "
                f"{self._dimensionality} axes, but was given a probe drive "
                f"with {len(self._axes)} axes."
            )

    def __call__(self, points, to_coords="drive"):
        r"""
        Perform a coordinate transformation on the supplied ``points``.

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
        tr_points: :term:`array_like`
            The points calculated from the coordinate transformation of
            ``points``.  The returned array has the same dimensionality
            as ``points``.

        """

        # make sure points is a numpy array
        if not isinstance(points, np.ndarray):
            points = np.array(points)

        # make sure points is always an M X N matrix
        if points.ndim == 1 and self.naxes == 1:
            points = points[np.newaxis, ...]
        elif points.ndim == 1:
            points = points[..., np.newaxis]

        # points always needs to be 2D
        if points.ndim != 2:
            raise ValueError(
                f"Expected a 2D array for 'points', but got a {points.ndim}-D"
                f"array."
            )

        # validate to_coords
        valid_coords = {"drive", "mspace", "motion_space", "motion space"}
        if not isinstance(to_coords, str):
            raise TypeError(
                f"For argument 'to_coords' expected type string, got type "
                f"{type(to_coords)}."
            )
        elif to_coords not in valid_coords:
            raise ValueError(
                f"For argument 'to_coords' expected a string value in "
                f"{valid_coords}, but got {to_coords}."
            )

        tr_points = self._convert(points, to_coords=to_coords)

        if tr_points.ndim not in (1, 2):
            ValueError(
                "Something went wrong! The coordinate transformed points "
                "do not share the same dimensionality as 'points'.  The"
                " is likely a developer error and not a user error.  "
                "Please post an issue on the bapsf_motion GitHub "
                "repo, https://github.com/BaPSF/bapsf_motion/issues."
            )
        elif tr_points.ndim == 1 and self.naxes == 1:
            tr_points = tr_points[np.newaxis, ...]
        elif tr_points.ndim == 1:
            tr_points = tr_points[..., np.newaxis]

        return tr_points

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
    def transform_type(self) -> str:
        """
        String naming the coordinate transformation type.  This is
        unique among all subclasses of `BaseTransform`.
        """
        return self._transform_type

    @property
    def dimensionality(self) -> int:
        """
        The designed dimensionality of the transform.  If ``-1``, then
        the transform does not have a fixed dimensionality, and it can
        morph to the associated |Drive|.
        """
        return self._dimensionality

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
            transformation matrix will be generated.  The array of
            points needs to be of size :math:`M` or :math:`M \times N`
            where :math:`M` is the dimensionality of the
            :term:`motion space` and :math:`N` is the number of points
            to be transformed.

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
        # Developer Notes:
        # 1. Call sequences goes
        #    __call__ -> _convert -> _matrix
        # 2. __call__ has conditioned points, so it will always be M x N
        # 3. __call__ has validated to_coords

        _matrix = (
            self._matrix_to_drive(points) if to_coords == "drive"
            else self._matrix_to_motion_space(points)
        )

        if _matrix.shape == tuple(2 * [self.naxes + 1]):
            return _matrix[..., np.newaxis]
        return _matrix

    def _convert(self, points, to_coords="drive"):
        r"""
        Perform the coordinate transform to convert points from probe
        drive coordinates to motion space coordinates, and vice versa.

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
        tr_points: :term:`array_like`
            The points calculated from the coordinate transformation of
            ``points``.  The returned array has the same dimensionality
            as ``points``.
        """
        # Developer Notes:
        # 1. Call sequences goes
        #    __call__ -> _convert
        # 2. Proper conditioning of 'points' has already been done s.t. an
        #    M x N numpy array will always be passed in...this could only NOT
        #    be the case if the subclass overrides methods upstream in the call
        #    sequence.
        # 3. Proper conditioning of 'to_coords has already been done
        #    by __call__
        # 4. The generated matrix for transformed points should always be of
        #    dimensionality M x N, that same as 'points'.

        # TODO: this convert function still need to be test to show
        #       that it'll work for N-dimensions...I stole this from
        #       LaPDXYTransform.convert() so it works in a world where
        #       the generated matrix _matrix() is 3x3 but the points/positions
        #       are only given as a 2-element vector

        matrix = self._matrix(points, to_coords=to_coords)

        if points.shape[1] == 1:
            points = np.concatenate((points[..., 0], [1]))
            return np.matmul(matrix, points)[:-1]

        # add in extra dimension for the translation axis
        points = np.concatenate(
            (points, np.ones((points.shape[0], 1))),
            axis=1,
        )
        return np.einsum("kmn,kn->km", matrix, points)[..., :-1]

    @abstractmethod
    def _matrix_to_drive(self, points):
        r"""
        Generate a transformation matrix that converts points from
        motion space coordinates to probe drive coordinates.

        Parameters
        ----------
        points: :term:`array_like`
            A single point or array of points in the motion space
            coordinate system for which the transformation matrix will
            be generated.  The array of points needs to be of size
            :math:`M` or :math:`M \times N` where :math:`M` is the
            dimensionality of the :term:`motion space` and :math:`N` is
            the number of points to be transformed.

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
        # Developer Notes:
        # 1. Call sequences goes
        #    __call__ -> _convert -> _matrix -> _matrix_to_drive
        # 2. Proper conditioning of points has already been done s.t. an
        #    M x N numpy array will always be passed in...this could only NOT
        #    be the case if the subclass overrides methods upstream in the call
        #    sequence.
        # 3. The generated matrix should always be of dimensionality
        #    M+1 x M+1 x N, where M is the motion space dimensionality and
        #    N is the number of points to convert...points has dimensionality
        #    M x N
        # 4. The +1 in the dimensionality corresponds to axis for coordinate
        #    translations.  If a transformation has no translation, then all
        #    values of this axis are zero.
        ...

    @abstractmethod
    def _matrix_to_motion_space(self, points):
        r"""
        Generate a transformation matrix that converts points from
        probe drive coordinates to motion space coordinates.

        Parameters
        ----------
        points: :term:`array_like`
            A single point or array of points in the probe drive
            coordinate system for which the transformation matrix will
            be generated.  The array of points needs to be of size
            :math:`M` or :math:`M \times N` where :math:`M` is the
            dimensionality of the :term:`motion space` and :math:`N` is
            the number of points to be transformed.

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
        # Developer Notes:
        # 1. Call sequences goes
        #    __call__ -> _convert -> _matrix -> _matrix_to_motion_space
        # 2. Proper conditioning of points has already been done s.t. an
        #    M x N numpy array will always be passed in...this could only NOT
        #    be the case if the subclass overrides methods upstream in the call
        #    sequence.
        # 3. The generated matrix should always be of dimensionality
        #    M+1 x M+1 x N, where M is the motion space dimensionality and
        #    N is the number of points to convert...points has dimensionality
        #    M x N
        # 4. The +1 in the dimensionality corresponds to axis for coordinate
        #    translations.  If a transformation has no translation, then all
        #    values of this axis are zero.
        ...
