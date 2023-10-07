"""
Module for functionality focused around the
`~bapsf_motion.actors.motion_group_.MotionGroup` actor class.
"""
__all__ = ["MotionGroup", "MotionGroupConfig"]
__actors__ = ["MotionGroup"]

import astropy.units as u
import asyncio
import logging
import numpy as np

from collections import UserDict
from pathlib import Path
from typing import Any, Dict, Optional, Union

from bapsf_motion.actors.base import EventActor
from bapsf_motion.actors.drive_ import Drive
from bapsf_motion.motion_builder import MotionBuilder
from bapsf_motion import transform
from bapsf_motion.utils import toml


_EXAMPLES = list((Path(__file__).parent / ".." / "examples").resolve().glob("*.toml"))


class MotionGroupConfig(UserDict):
    """
    A dictionary containing the full configuration for a motion group.

    At instantiation the class will take either a TOML-like string or
    dictionary defining a motion group configuration.  The class will
    validate this input configuration, convert it to a viable
    dictionary configuration, and poses it as `self`.

    Parameters
    ----------
    config: `str` or `dict`
        A TOML like string or dictionary defining the motion group
        configuration.  See examples section below for additional
        details.

    Examples
    --------

    The following example shows how a typical XY probe drive on an East
    port of the LaPD could be configured using either a TOML-like string
    or a dictionary.  Note, values used are not necessarily appropriate
    for a real world setup.

    .. tabs::

       .. code-tab:: toml TOML

          [motion_group]
          name = "P32 XY-drive"  # unique name of motion group

          [motion_group.drive]
          # define the makeup of the probe drive
          name = "XY-drive"  # name of probe drive
          #
          # setup first axis
          axes.0.name = "X"  # name of axis
          axes.0.ip = "192.168.6.103"  # ip address of motor
          axes.0.units = "cm"  # unit type used for axis
          axes.0.units_per_rev = 0.254  # thread pitch of rod
          #
          # setup second axis
          axes.1.name = "Y"
          axes.1.ip = "192.168.6.104"
          axes.1.units = "cm"
          axes.1.units_per_rev = 0.254

          [motion_group.motion_builder]
          # configuration for the motion builder
          #
          # 'space' defines the motion space
          # - motion space is the "volume" in which the motion will
          #   occur in
          # - these axes correspond to the same 0 and 1 axes of the
          #   motion_group.drive.axes configuration
          space.0.label = "X"
          space.0.range = [-55, 55]
          space.0.num = 221
          space.1.label = "Y"
          space.1.range = [-55, 55]
          space.1.num = 221
          #
          # exclusion defines regions in space where a probe can NOT go
          # - exclusion entries should be numbered starting with 0 since
          #   complex exclusions can be construction from multiple
          #   exclusion layers
          # - an exclusion always requires the 'type' parameter, but
          #   the subsequent required parameters depend on that type
          # - See online documentation for available exclusion layers.
          exclusions.0.type = "lapd_xy"
          exclusions.0.port_location = "E"
          exclusions.0.cone_full_angle = 60
          #
          # layers define the points where a probe should move to
          # - the example given defines a grid of points wih 11
          #   locations along the 1st axis from 0 to 30, and 21
          #   locations along the 2nd axis from -30 to 30
          # - layer entries should be numbered starting with 0 since
          #   complex point layers can be construction from multiple
          #   point layers
          # - a layer always requires the 'type' parameter, but
          #   the subsequent required parameters depend on that type
          # - See online documentation for available point layers.
          layers.0.type = "grid"
          layers.0.limits = [[0, 30], [-30, 30]]
          layers.0.steps = [11, 21]

          [motion_group.transform]
          # define the coordinate transformation between the physical
          # coordinate system, a.k.a. motion space, (e.g. the LaPD) and
          # the probe drive axes
          # - a transform always requires the 'type' parameter, but
          #   the subsequent required parameters depend on that type
          # - See online documentation for available point layers.
          type = "lapd_xy"
          pivot_to_center = 57.7
          pivot_to_drive = 125
          porbe_axis_offset = 6


       .. code-tab:: py Dict Entry

          # Look to the TOML tab for descriptions of each entry
          config = {
              "name": "P32 XY-Drive",
              "drive": {
                  "name": "XY-Drive",
                  "axes": {
                      0: {
                          "name": "X",
                          "ip": "192.168.6.103",
                          "units": "cm",
                          "units_per_rev": .254,
                      },
                      1: {
                          "name": "Y",
                          "ip": "192.168.6.104",
                          "units": "cm",
                          "units_per_rev": .254,
                      },
                  },
              },
              "motion_builder": {
                  "space", {
                      0: {
                          "label": "X",
                          "range": [-55, 55],
                          "num:: 221,
                      },
                      1: {
                          "label": "X",
                          "range": [-55, 55],
                          "num:: 221,
                      },
                  },
                  "exclusions": {
                      "0": {
                          "type": "lapd_xy",
                          "port_location": "E",
                          "cone_full_angle": 60,
                      },
                  },
                  "layers": {
                      "0": {
                          "type": "grid",
                          "limits": [[0, 30], [-30, 30]],
                          "steps": [11, 21],
                      },
                  },
              },
              "transform": {
                  "type": "lapd_xy",
                  "pivot_to_center": 57.7,
                  "pivot_to_drive": 125,
                  "porbe_axis_offset": 6,
              },
          }

    """
    #: required keys for the motion group configuration dictionary
    _required_metadata = {
        "motion_group": {
            "name",
            "drive",
            "transform",
            "motion_builder",
        },
        "drive": {"name", "axes"},
        "drive.axes": {"ip", "units", "name", "units_per_rev"},
        "transform": {"type"},
        "motion_builder": {"space"},
        "motion_builder.exclusions": {"type"},
        "motion_builder.layers": {"type"},
        # "motion_builder.space": {"label", "range", "num"},
    }

    #: optional keys for the motion group configuration dictionary
    _optional_metadata = {
        "motion_builder": {"exclusions", "layers"},
    }

    #: allowable motion group header names
    _mg_names = {"motion_group", "mgroup", "mg"}

    def __init__(self, config: Union[str, Dict[str, Any]]):

        # Make sure config is the right type, and is a dict by the
        # end of ths code block
        if isinstance(config, MotionGroupConfig):
            # This would happen if Manager is passing in a configuration
            pass
        elif isinstance(config, str):
            # Assume config is a TOML like string
            config = toml.loads(config)
        elif not isinstance(config, dict):
            raise TypeError(
                f"Expected 'config' to be of type dict, got type {type(config)}."
            )

        # Check if the configuration has a motion group header or just
        # the configuration
        mg_names = self._mg_names
        if len(mg_names - set(config.keys())) < len(mg_names) - 1:
            raise ValueError(
                "Unable to interpret configuration, since there appears"
                " to be multiple motion group configurations supplied."
            )
        elif len(mg_names - set(config.keys())) == len(mg_names) - 1:
            # mg_name found in config
            mg_name = tuple(mg_names - (mg_names - set(config.keys())))[0]
            config = config[mg_name]

            if not isinstance(config, dict):
                raise TypeError(
                    f"Expected 'config' to be of type dict, "
                    f"got type {type(config)}."
                )

        if "name" not in config and len(config) != 1:
            raise ValueError(
                "Unable to interpret configuration, since there appears"
                " to be multiple motion group configurations supplied."
            )
        elif "name" not in config:
            config = list(config.values())[0]

            if not isinstance(config, dict):
                raise TypeError(
                    f"Expected 'config' to be of type dict, "
                    f"got type {type(config)}."
                )

        # validate config
        config = self._validate_config(config)
        self._drive = None
        self._transform = None
        self._motion_builder = None

        super().__init__(config)
        self._data = self.data

    @property
    def data(self):
        """
        A real dictionary used to store the contents of
        `MotionGroupConfig`.
        """
        if self._drive is not None:
            self._data = {**self._data, "drive": self._drive.config}

        if self._motion_builder is not None:
            self._data = {**self._data, "motion_builder": self._motion_builder.config}

        if self._transform is not None:
            self._data = {**self._data, "transform": self._transform.config}

        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the motion group configuration dictionary."""

        # Check for root level required key-value pairs
        missing_meta = self._required_metadata["motion_group"] - set(config.keys())
        if missing_meta:
            raise ValueError(
                f"Supplied configuration is missing required root level "
                f"keys {missing_meta}."
            )

        config["name"] = str(config["name"])
        config["drive"] = self._validate_drive(config["drive"])
        config["transform"] = self._validate_transform(config["transform"])
        config["motion_builder"] = self._validate_motion_builder(config["motion_builder"])

        config = self._handle_user_meta(config, self._required_metadata["motion_group"])

        # TODO: the below commented out code block is not do-able since
        #       motion_builder.space can be defined as a string for builtin spaces
        #       or ranges for all axes...once this is reconciled then the
        #       code block below can be reinstated.
        #
        # # check axis names are the same as the motion builder labels
        # axis_labels = (ax["name"] for ax in config["drive"]["axes"].values())
        # ml_labels = tuple(config["motion_builder"]["label"])
        # if axis_labels != ml_labels:
        #     raise ValueError(
        #         f"The Motion List space and Axes must have the same "
        #         f"ordered names, got {ml_labels} and {axis_labels} "
        #         f"respectively."
        #     )

        return config

    def _validate_drive(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the drive component of the motion group configuration.
        """
        req_meta = self._required_metadata["drive"]

        missing_meta = req_meta - set(config.keys())
        if missing_meta:
            raise ValueError(
                f"Supplied configuration for Drive is missing required "
                f"keys {missing_meta}."
            )

        config = self._handle_user_meta(config, req_meta)

        ax_meta = set(config["axes"].keys())
        if len(self._required_metadata["drive.axes"] - ax_meta) == 0:
            # assume drive only has one axis
            ax_config = config.pop("axes")
            config["axes"][0] = ax_config

        for ax_id, ax_config in config["axes"].items():
            # TODO: is there a good way of enforcing ax_id to be an int
            #       starting at 0 and monotonically increasing
            config["axes"][ax_id] = self._validate_axis(ax_config)

        # ensure all axis names and ips are unique
        naxes = len(config["axes"])
        for key in {"name", "ip"}:
            vals = [val[key] for val in config["axes"].values()]

            if len(set(vals)) != naxes:
                raise ValueError(
                    f"The axes of the configured probe drive do NOT have"
                    f" unique {key}s.  The drive has {naxes} and only "
                    f"{len(set(vals))} unique {key}s, {set(vals)}."
                )

        return config

    def _validate_axis(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the axis (e.g. axes.0) component of the drive
        component of the motion group configuration.
        """
        req_meta = self._required_metadata["drive.axes"]

        missing_meta = req_meta - set(config.keys())
        if missing_meta:
            raise ValueError(
                f"Supplied configuration for Axis is missing required "
                f"keys {missing_meta}."
            )

        config = self._handle_user_meta(config, req_meta)

        # TODO: Is it better to do the type checks here or allow class
        #       instantiation to handle it.

        return config

    def _validate_motion_builder(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the motion builder component of the motion group
        configuration.
        """
        req_meta = self._required_metadata["motion_builder"]
        opt_meta = self._optional_metadata["motion_builder"]

        missing_meta = req_meta - set(config.keys())
        if missing_meta:
            raise ValueError(
                f"Supplied configuration for MotionBuilder is missing required "
                f"keys {missing_meta}."
            )

        config = self._handle_user_meta(config, set.union(req_meta, opt_meta))

        # now check for requited meta keys of the lower level required
        # keys (i.e. layers and exceptions)
        for key in opt_meta:
            try:
                sub_config = config[key]
            except KeyError:
                continue

            if not isinstance(sub_config, dict):
                raise TypeError(
                    f"Expected type dict for the motion_builder.{key} configuration,"
                    f" got type {type(sub_config)}."
                )

            try:
                rmeta = self._required_metadata[f"motion_builder.{key}"]
            except KeyError:
                continue

            if "type" in sub_config.keys():
                # there's only 1 item with required meta 'type'

                missing_meta = rmeta - set(sub_config.keys())
                if missing_meta:
                    raise ValueError(
                        f"Supplied configuration for motion_builder.{key} is "
                        f"missing required  keys {missing_meta}."
                    )

                config[key][0] = config.pop(key)

                continue

            for sck, scv in sub_config.items():
                if not isinstance(scv, dict):
                    raise ValueError(
                        f"Expected type dict for the motion_builder.{key}.{sck} "
                        f"configuration, got type {type(sub_config)}."
                    )

                missing_meta = rmeta - set(scv.keys())
                if missing_meta:
                    raise ValueError(
                        f"Supplied configuration for motion_builder.{key}.{sck} is "
                        f"missing required  keys {missing_meta}."
                    )

        return config

    def _validate_transform(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the transform component of the motion group
        configuration.
        """
        req_meta = self._required_metadata["transform"]

        missing_meta = req_meta - set(config.keys())
        if missing_meta:
            raise ValueError(
                f"Supplied configuration for Transformer is missing required "
                f"keys {missing_meta}."
            )
        return config

    @staticmethod
    def _handle_user_meta(config: Dict[str, Any], req_meta: set) -> Dict[str, Any]:
        """
        If a user specifies metadata that is not required by a specific
        configuration component, then collect all the metadata and
        store it under the 'user' key.  Return the modified dictionary.
        """
        user_meta = set(config.keys()) - req_meta

        if len(user_meta) == 0:
            return config

        if "user" in user_meta:
            user_meta.remove("user")

            if not isinstance(config["user"], dict):
                raise ValueError(
                    "The 'user' metadate field `config['user']` must be a dict,"
                    f" got type {type(config['user'])}."
                )
        else:
            config["user"] = dict()

        for key in user_meta:
            config["user"][key] = config.pop(key)

        if len(config["user"]) == 0:
            del config["user"]

        return config

    def link_motion_builder(self, mb: MotionBuilder):
        """
        Link the 'motion_builder' configuration component to an instance
        of |MotionBuilder|.  The 'motion_builder' configuration component
        will now be pulled from the :attr:`config` property of
        |MotionBuilder|.
        """
        if not isinstance(mb, MotionBuilder):
            raise TypeError(
                f"For argument 'mb' expected type {MotionBuilder}, but got "
                f"type {type(mb)}."
            )

        self._motion_builder = mb

    def link_drive(self, drive: Drive):
        """
        Link the 'drive' configuration component to an instance  of
        |Drive|.  The 'drive' configuration component  will now be
        pulled from the :attr:`config` property of |Drive|.
        """
        if not isinstance(drive, Drive):
            raise TypeError(
                f"For argument 'drive' expected type {Drive}, but got "
                f"type {type(drive)}."
            )

        self._drive = drive

    def link_transform(self, tr: transform.BaseTransform):
        """
        Link the 'transform' configuration component to an instance of
        a subclass of `~bapsf_motion.transform.base.BaseTransform`.
        The 'transform' configuration component  will now be
        pulled from the :attr:`config` property of that transform
        instance.
        """
        if not isinstance(tr, transform.BaseTransform):
            raise TypeError(
                f"For argument 'tr' expected a subclass of "
                f"{transform.BaseTransform}, but got type {type(tr)}."
            )

        self._transform = tr


class MotionGroup(EventActor):
    r"""
    The `MotionGroup` actor brings together all the components that
    are needed to move a probe drive around the motion space.  These
    components include: (1) the full motion group configuration
    (i.e. instance of `MotionGroupConfig`), (2) communication with
    the probe drive (i.e. instance of |Drive|), (3) an understanding
    of the motion space (i.e. instance of |MotionBuilder|, and (4) how
    to convert back and forth from the motion space coordinate system
    and the probe drive coordinate system (i.e. instance of a subclass
    of `~bapsf_motion.transform.base.BaseTransform`).

    Parameters
    ----------
    config:`str` or `dict`
        A TOML like string or dictionary defining the motion group
        configuration.  See `MotionGroupConfig` for further details.

    logger: `~logging.Logger`, optional
        An instance of `~logging.Logger` that the Actor will record
        events and status updates to.  If `None`, then a logger will
        automatically be generated. (DEFAULT: `None`)

    loop: `asyncio.AbstractEventLoop`, optional
        Instance of an `asyncio` `event loop`_. Communication with all
        the axes will happen primarily through the event loop.  If
        `None`, then an `event loop`_ will be auto-generated.
        (DEFAULT: `None`)

    auto_run: bool, optional
        If `True`, then the `event loop`_ will be placed in a separate
        thread and started.  This is all done via the :meth:`run`
        method. (DEFAULT: `False`)
    """
    # TODO: update docstring to fully explain how to define the `config`
    #       argument
    # TODO: Add a keyword 'mode' that changes how restrictive
    #       instantiation is.  For example,
    #       1. 'run' would be very restrictive since it's intended for
    #          a data run
    #       2. 'build' would be relaxed since it is intended as a
    #          configuration build mode
    #       3. 'test' would probably be inbetween the the above two
    #          mode since it's intended for debugging purposes
    def __init__(
        self,
        config: Union[str, Dict[str, Any]] = None,
        *,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
    ):

        config = MotionGroupConfig(config)

        super().__init__(
            name=config["name"],
            logger=logger,
            loop=loop,
            auto_run=False,
        )

        self._drive = self._spawn_drive(config["drive"])

        self._mb = self._setup_motion_builder(config["motion_builder"])
        self._ml_index = None

        self._transform = self._setup_transform(config["transform"])

        self._config = config
        self._config.link_drive(self.drive)
        self._config.link_motion_builder(self.mb)
        self._config.link_transform(self.transform)

        self.run(auto_run=auto_run)

    def _configure_before_run(self):
        return

    def _initialize_tasks(self):
        return

    def _spawn_drive(
        self, config: Dict[str, Any]
    ) -> Drive:
        """
        Spawn and return the |Drive| instance for the motion group.

        Parameters
        ----------
        config: `dict`
            Drive component of the motion group configuration.
        """

        dr = Drive(
            axes=list(config["axes"].values()),
            name=config["name"],
            logger=self.logger,
            loop=self.loop,
            auto_run=False,
        )
        return dr

    @staticmethod
    def _setup_motion_builder(config: Dict[str, Any]) -> MotionBuilder:
        """Return an instance of |MotionBuilder|."""
        # initialize the motion builder object

        ml_config = config.copy()

        for key in {"name", "user"}:
            try:
                ml_config.pop(key)
            except KeyError:
                pass

        for key in {"space", "layers", "exclusions"}:
            try:
                ml_config[key] = list(ml_config.pop(key).values())
            except KeyError:
                continue

        _ml = MotionBuilder(**ml_config)
        return _ml

    def _setup_transform(self, config: Dict[str, Any]) -> transform.BaseTransform:
        """Return an instance of the :term:`transformer`."""

        tr_config = config.copy()

        tr_type = tr_config.pop("type")
        return transform.transform_factory(self.drive, tr_type=tr_type, **config)

    def terminate(self, delay_loop_stop=False):
        self.drive.terminate(delay_loop_stop=True)
        super().terminate(delay_loop_stop=delay_loop_stop)

    @property
    def config(self):
        return self._config
    config.__doc__ = EventActor.config.__doc__

    @property
    def drive(self) -> Drive:
        """Instance of |Drive| associated with the motion group."""
        return self._drive

    @property
    def mb(self) -> MotionBuilder:
        """Instance of |MotionBuilder| associated with the motion group."""
        return self._mb

    @property
    def ml_index(self):
        """Last motion list index the probe drive moved to."""
        return self._ml_index

    @ml_index.setter
    def ml_index(self, index):
        if index is None:
            self._ml_index = None
        elif not isinstance(index, (int, np.integer)):
            raise ValueError(
                f"Expected type int for 'index', got {type(index)}"
            )
        elif not np.isin(index, self.mb.motion_list.index):
            raise ValueError(
                f"Given index {index} is out of range, "
                f"[0, {self.mb.motion_list.index.size}]."
            )

        self._ml_index = index

    @property
    def transform(self) -> transform.BaseTransform:
        """
        Instance of the :term:`transformer` associated with the motion
        group.
        """
        return self._transform

    @property
    def position(self) -> u.Quantity:
        """
        Current position of the probe drive, in motion space
        coordinates and units.
        """
        dr_pos = self.drive.position
        pos = self.transform(
            dr_pos.value.tolist(),
            to_coords="motion_space",
        )
        return pos * dr_pos.unit

    def stop(self):
        """Immediately stop the probe drive motion."""
        self.drive.stop()

    def move_to(self, pos, axis: Optional[int] = None):
        """
        Move the probe drive to a specified location, ``pos``.

        Parameters
        ----------
        pos: :term:`array_like`
            A position in the :term:`motion space` for the probe to be
            moved to.  ``pos`` should have the same dimensionality as
            the motion space unless keyword ``axis`` is used.

        axis: `int`, optional
            An integer specifying which axis is to be moved.  ``axis``
            is integer of 0 to :math:`N-1`, where :math:`N` is the
            dimensionality of the motion space.
        """
        if isinstance(pos, u.Quantity):
            pos = pos.value

        dr_pos = self.transform(pos, to_coords="drive")
        return self.drive.move_to(pos=dr_pos, axis=axis)

    def move_ml(self, index: int):
        """
        Move the probe drive to a specific index of the motion list.
        """
        if index == "next":
            index = 0 if self.ml_index is None else self.ml_index + 1
        elif index == "first":
            index = 0
        elif index == "last":
            index = self.mb.motion_list.index[-1].item()

        self.ml_index = index
        pos = self.mb.motion_list.sel(index=index).to_numpy().tolist()

        return self.move_to(pos=pos)
