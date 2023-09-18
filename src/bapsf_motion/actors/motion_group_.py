"""
Module for functionality focused around the
`~bapsf_motion.actors.motion_group_.MotionGroup` actor class.
"""
__all__ = ["MotionGroup", "MotionGroupConfig"]
__actors__ = ["MotionGroup"]

import numpy as np
import tomli

from collections import UserDict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.drive_ import Drive
from bapsf_motion.motion_list import MotionList
from bapsf_motion import transform

_EXAMPLES = list((Path(__file__).parent / ".." / "examples").resolve().glob("*.toml"))


class MotionGroupConfig(UserDict):
    _required_metadata = {
        "mgroup": {
            "name",
            "axes",
            "transform",
            "motion_list",
        },
        "axes": {"ip", "units", "name", "units_per_rev"},
        "transform": {
            "type",
            "droop_correction",
            "pivot_to_center",
            "pivot_to_clamp",
            "zero_to_home",
        },
        "motion_list": {"space", "exclusions", "layers"},
        "motion_list.space": {"label", "range", "num"},
    }

    def __init__(
        self,
        *,
        filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        # ensure filename XOR config kwargs are specified
        if filename is None and config is None:
            raise TypeError(
                "MotionGroup() missing 1 required keyword argument: use "
                "'filename' or 'config' to specify a configuration."
            )
        elif filename is not None and config is not None:
            raise TypeError(
                "MotionGroup() takes 1 keyword argument but 2 were "
                "given: use keyword 'filename' OR 'config' to specify "
                "a configuration."
            )
        elif filename is not None:
            filename = Path(filename).resolve()

            if not filename.exists():
                for efile in _EXAMPLES:
                    if filename.name == efile.name:
                        filename = efile
                        break

            if not filename.exists():
                raise ValueError(
                    f"Specified Motion Group configuration file does "
                    f"not exist, {filename}."
                )

            with open(filename, "rb") as f:
                config = tomli.load(f)

        if "mgroup" in config and len(config) != 1:
            raise ValueError(
                "Supplied configuration unrecognized, suspected "
                "multiple Motion Groups defined."
            )
        elif "mgroup" in config:
            config = config["mgroup"]

        config = self._validate_config(config)

        super().__init__(config)

    def _validate_config(self, config):
        if len(config) == 1:
            key, val = tuple(config.items())[0]
            if key.isnumeric():
                config = val
            else:
                raise ValueError(
                    "Supplied configuration is unrecognized, only one "
                    "key-value pair defined."
                )

        missing_configs = self._required_metadata["mgroup"] - set(config.keys())
        if missing_configs:
            raise ValueError(
                f"Supplied configuration is missing required keys {missing_configs}."
            )

        config["name"] = str(config["name"])

        config["axes"] = self._validate_axes(config["axes"])
        config["transform"] = self._validate_transform(config["transform"])
        config["motion_list"] = self._validate_motion_list(config["motion_list"])

        # check axis names are the same as the motion list labels
        axis_labels = (ax["name"] for ax in config["axes"])
        ml_labels = tuple(config["motion_list"]["label"])
        if axis_labels != ml_labels:
            raise ValueError(
                f"The Motion List space and Axes must have the same "
                f"ordered names, got {ml_labels} and {axis_labels} "
                f"respectively."
            )

        return config

    def _validate_axes(self, config):
        valid_config = []
        req_meta = self._required_metadata["axes"]

        if set(config.keys()) != req_meta:
            raise ValueError(
                "Axis configuration is missing keys or has unrecognized "
                f"keys.  Got {set(config.keys())}, but expected {req_meta}."
            )

        for key, val in config.items():
            if not isinstance(val, (list, tuple)):
                config[key] = (val,)

        naxes = len(config["ip"])

        if any(len(val) != naxes for val in config.values()):
            raise ValueError(
                "Axis configuration is invalid.  All keys need to "
                f"lists of equal length."
            )
        elif len(set(config["name"])) != len(config["name"]):
            raise ValueError(
                "Axis 'name' configuration must be unique for each axis,"
                f" got {config['name']}."
            )

        for ii in range(naxes):
            ax_dict = {}
            for key in req_meta:
                ax_dict[key] = config[key][ii]

            valid_config.append(ax_dict)

        # indices = None
        # if all(key.isnumeric() for key in config.keys()):
        #     indices = set(key for key in config.keys())
        #
        # if indices is None:
        #     indices = {"0"}
        #     config = {"0": config}
        #
        # for index in indices:
        #     val = config[index]
        #
        #     if set(val.keys()) != req_meta:
        #         raise ValueError(
        #             "Axis configuration is missing keys or has unrecognized "
        #             f"keys.  Got {set(val.keys())}, but expected {req_meta}."
        #         )
        #
        #     valid_config.append(val)

        return valid_config

    def _validate_motion_list(self, config):

        if set(config.keys()) != self._required_metadata["motion_list"]:
            raise ValueError(
                "Motion List configuration is missing or has unrecognized"
                f" keys, got {set(config.keys())} and expected "
                f"{self._required_metadata['motion_list']}."
            )

        space_config = config["space"]
        if set(space_config.keys()) != self._required_metadata["motion_list.space"]:
            raise ValueError(
                "Motion List 'space' configuration is missing or has "
                f"unrecognized keys, got {set(space_config.keys())} and "
                f"expected "
                f"{self._required_metadata['motion_list.space']}."
            )

        for key, val in space_config.items():
            if not isinstance(val, (list, tuple)):
                space_config[key] = [val, ]

        naxes = len(space_config["label"])
        if any(len(val) != naxes for val in space_config.values()):
            raise ValueError(
                "Motion List 'space' configuration is invalid.  All "
                "keys need to be lists of equal length."
            )

        # TODO: pickup validation work here ...

        return config

    def _validate_transform(self, config):
        return config

    @property
    def drive_settings(self) -> Iterable[Dict[str, Any]]:
        axes = self["axes"]
        naxes = len(axes["ip"])
        settings = [{}, {}]
        for ii in range(naxes):
            for key, val in axes.items():
                settings[ii][key] = val[ii]

        return settings


class MotionGroup(BaseActor):
    def __init__(
        self,
        *,
        filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        logger=None,
        loop=None,
        auto_run=False,
    ):
        config = self._process_config(filename=filename, config=config)

        super().__init__(logger=logger, name=config["name"])

        self._drive = self._spawn_drive(config["drive"], loop)

        self._ml = self._setup_motion_list(config["motion_list"])
        self._ml_index = None

        self._transform = self._setup_transform(config["transform"])

        # self._validate_setup()

        if auto_run:
            self.run()

    @staticmethod
    def _process_config(
        *,
        filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        # ensure filename XOR config kwargs are specified
        if filename is None and config is None:
            raise TypeError(
                "MotionGroup() missing 1 required keyword argument: use "
                "'filename' or 'config' to specify a configuration."
            )
        elif filename is not None and config is not None:
            raise TypeError(
                "MotionGroup() takes 1 keyword argument but 2 were "
                "given: use keyword 'filename' OR 'config' to specify "
                "a configuration."
            )
        elif filename is not None:
            filename = Path(filename).resolve()

            if not filename.exists():
                for efile in _EXAMPLES:
                    if filename.name == efile.name:
                        filename = efile
                        break

            if not filename.exists():
                raise ValueError(
                    f"Specified Motion Group configuration file does "
                    f"not exist, {filename}."
                )

            with open(filename, "rb") as f:
                config = tomli.load(f)

        # trim so we're at the motion group root config
        if "mgroup" in config and len(config) != 1:
            raise ValueError(
                "Supplied configuration unrecognized, suspected "
                "multiple Motion Groups defined."
            )
        elif "mgroup" in config:
            config = config["mgroup"]

        # validate root level config
        # _required_metadata = {"name", "drive", "motion_list", "transform"}
        # _required_metadata = {"name", "drive", "motion_list"}
        # TODO: "motion_list" should be optional under certain situations,
        #       but not others...e.g. ml is required during a run but
        #       not one off operation

        if len(config) == 1:
            key, val = tuple(config.items())[0]
            if key.isnumeric():
                config = val
            else:
                raise ValueError(
                    "Supplied configuration is unrecognized, only one "
                    "key-value pair defined."
                )

        _required_metadata = {"name", "drive"}
        missing_configs = _required_metadata - set(config.keys())
        if missing_configs:
            raise ValueError(
                f"Supplied configuration is missing required keys {missing_configs}."
            )

        config["name"] = str(config["name"])

        if "motion_list" not in config:
            config["motion_list"] = None

        if "transform" not in config:
            config["transform"] = None

        return config

    def _spawn_drive(self, config, loop) -> Drive:
        """
        The Drive configuration should look like:

        .. code-block:

            config = {
                "name": "probe_drive_name",
                "axes": {
                    "ip": ["192.168.0.70", "192.168.0.80"],
                    "name": ["x", "y"],
                    "units": ["cm", "cm"],
                    "units_per_rev": [0.254, 0.254],
                },
            }

        or

        .. code-block:

            config = {
                "name": "probe_drive_name",
                "axes": [
                    {
                        "ip": "192.168.0.70",
                        "name": "x",
                        "units": "cm",
                        "units_per_rev": 0.256,
                    },
                    {
                        "ip": "192.168.0.80",
                        "name": "y",
                        "units": "cm",
                        "units_per_rev": 0.256,
                    },
                ],
            }

        Both version are acceptable, but the latter is what gets passed
        to Drive and the former comes from the TOML files.
        """
        if "axes" not in config:
            raise ValueError(
                "The Drive configuration for the motion group does"
                f" NOT specify any axes.  Got {config}."
            )
        elif isinstance(config["axes"], dict):
            axes = config["axes"]
            new_axes = []
            keys = list(axes.keys())
            size = len(axes[keys[0]])
            for ii in range(size):
                ax = {}
                for key in keys:
                    ax[key] = axes[key][ii]

                new_axes.append(ax)

            config["axes"] = new_axes

        dr = Drive(
            logger=self.logger,
            loop=loop,
            auto_run=False,
            **config,
        )
        return dr

    def _setup_motion_list(self, config):
        # initialize the motion list object

        if config is None:
            return

        # re-pack exclusions
        exclusions = []
        for val in config["exclusions"].values():
            exclusions.append(val)
        config["exclusions"] = exclusions

        # re-pack layers
        layers = []
        for val in config["layers"].values():
            layers.append(val)
        config["layers"] = layers

        _ml = MotionList(**config)
        return _ml

    def _setup_transform(self, config: Dict[str, Any]):
        # initialize the transform object, this is used to convert between
        # LaPD coordinates and drive coordinates
        if config is None:
            raise ValueError(
                "Currently, the only valid transform is 'lapd_xy'."
            )
        elif "type" not in config:
            raise ValueError(
                "Transform configuration my missing key/value pair "
                "'type'."
            )

        tr_type = config.pop("type")
        return transform.transform_factory(self.drive, tr_type=tr_type, **config)

    def run(self):
        if self.drive is not None:
            self.drive.run()

    def stop_running(self, delay_loop_stop=False):
        if self.drive is None:
            return

        self.drive.stop_running(delay_loop_stop=delay_loop_stop)

    @property
    def config(self):
        return {
            "name": self.name,
            "drive": self.drive.config,
            "motion_list": self.ml.config,
            "transform": self.transform.config,
        }

    @property
    def drive(self):
        return self._drive

    @property
    def ml(self):
        return self._ml

    @property
    def ml_index(self):
        return self._ml_index

    @ml_index.setter
    def ml_index(self, index):
        if index is None:
            self._ml_index = None
        elif not isinstance(index, (int, np.integer)):
            raise ValueError(
                f"Expected type int for 'index', got {type(index)}"
            )
        elif not np.isin(index, self.ml.motion_list.index):
            raise ValueError(
                f"Given index {index} is out of range, "
                f"[0, {self.ml.motion_list.index.size}]."
            )

        self._ml_index = index

    @property
    def transform(self) -> "transform.LaPDXYTransform":
        return self._transform

    @property
    def position(self):
        dr_pos = self.drive.position
        pos = self.transform(
            dr_pos.value.tolist(),
            to_coords="motion_space",
        )
        return pos * dr_pos.unit

    def stop(self):
        self.drive.stop()

    def move_to(self, pos, axis=None):
        dr_pos = self.transform(pos, to_coords="drive")
        return self.drive.move_to(pos=dr_pos, axis=axis)

    def move_ml(self, index):
        if index == "next":
            index = 0 if self.ml_index is None else self.ml_index + 1
        elif index == "first":
            index = 0
        elif index == "last":
            index = self.ml.motion_list.index[-1].item()

        self.ml_index = index
        pos = self.ml.motion_list.sel(index=index).to_numpy().tolist()

        return self.move_to(pos=pos)

    def replace_motion_list(self, config):
        self._ml = self._setup_motion_list(config)
        self.ml_index = None

    def _validate_setup(self):
        # Needs to enforce that the drive, motion list, and transform
        # are all valid with respect to each other.  The following
        # should be validated.
        # 1. All elements have the same axis dimensionality
        # 2. All share the same naming for the axes
        ...
