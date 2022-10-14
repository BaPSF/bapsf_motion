__all__ = ["MotionGroup"]

import logging
import tomli

from collections import UserDict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.drive_ import Drive

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
        super().__init__(logger=logger, name="MGroup")

        self._config = MotionGroupConfig(filename=filename, config=config)
        self._initialize_motion_list()
        self._initialize_transform()
        self._drive = Drive(
            axes=self.config.drive_settings,
            logger=self.logger,
            loop=loop,
            auto_run=False,
        )

        if auto_run:
            self.run()

    def _initialize_motion_list(self):
        # initialize the motion list object
        ...

    def _initialize_transform(self):
        # initialize the transform object, this is used to convert between
        # LaPD coordinates and drive coordinates
        ...

    def run(self):
        if self.drive is not None:
            self.drive.run()

    def stop_running(self, delay_loop_stop=False):
        if self.drive is None:
            return

        self.drive.stop_running(delay_loop_stop=delay_loop_stop)

    @property
    def config(self):
        return self._config

    @property
    def drive(self):
        return self._drive
