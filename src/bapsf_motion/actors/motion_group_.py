__all__ = ["MotionGroup"]

import logging
import tomli

from collections import UserDict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from bapsf_motion.actors.drive_ import Drive

_EXAMPLES = list((Path(__file__).parent / ".." / "examples").resolve().glob("*.toml"))


class MotionGroupConfig(UserDict):
    _required_metadata = {
        "mgroup": {
            "name",
            "port_number",
            "port_orientation",
            "axis",
            "transform",
            "motion_list",
        },
        "axis": {"ip", "units", "name", "units_per_rev"},
        "transform": {
            "type",
            "droop_correction",
            "pivot_to_center",
            "pivot_to_clamp",
            "zero_to_home",
        },
        "motion_list": {"type", "n", "center", "size"},
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

            if len(config) == 1:
                config = list(config.values())[0]

        super().__init__(config)

    def _validate_config(self):
        ...

    def _validate_axis(self):
        ...

    def _validate_motion_list(self):
        ...

    def _validate_transform(self):
        ...

    @property
    def drive_settings(self) -> Iterable[Dict[str, Any]]:
        axes = self["axes"]
        naxes = len(axes["ip"])
        settings = [{}, {}]
        for ii in range(naxes):
            for key, val in axes.items():
                settings[ii][key] = val[ii]

        return settings


class MotionGroup:
    def __init__(
        self,
        *,
        filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        logger=None,
        loop=None,
        auto_run=False,
    ):
        self.setup_logger(logger, "MGroup")
        self._config = MotionGroupConfig(filename=filename, config=config)
        self._drive = Drive(
            axes=self.config.drive_settings,
            logger=self.logger,
            loop=loop,
            auto_run=False,
        )

        if auto_run:
            self.run()

    def setup_logger(self, logger, name):
        log_name = __name__ if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"
            self._name = name
        self._logger = logging.getLogger(log_name)

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

    @property
    def logger(self):
        return self._logger
