__all__ = ["MotionGroup"]

import tomli

from collections import UserDict
from typing import Any, Dict, Optional


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


class MotionGroup:
    def __init__(self, *, filename: str = None, config=None):
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

        self.config = None
        self.drive = None
