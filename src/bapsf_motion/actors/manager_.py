"""
Module for functionality focused around the
`~bapsf_motion.actors.manager_.Manager` actor class.
"""

__all__ = ["Manager"]
__actors__ = ["Manager"]

import asyncio
import logging

from collections import UserDict
from typing import Any, Dict, Union

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.motion_group_ import MotionGroup, MotionGroupConfig
from bapsf_motion.utils import toml


class ManagerConfig(UserDict):
    _manager_names = {"run"}

    def __init__(self, config: Union[str, Dict[str, Any]]):

        # Make sure config is the right type, and is a dict by the
        # end of ths code block
        if isinstance(config, ManagerConfig):
            # This should never happen ...
            pass
        elif isinstance(config, str):
            # Assume config is a TOML like string
            config = toml.loads(config)
        elif not isinstance(config, dict):
            raise TypeError(
                f"Expected 'config' to be of type dict, got type {type(config)}."
            )

        # Check if the configuration has a data run header or just
        # the configuration
        if len(self._manager_names - set(config.keys())) < len(self._manager_names) - 1:
            raise ValueError(
                "Unable to interpret configuration, since there appears"
                " to be multiple data run configurations supplied."
            )
        elif (len(self._manager_names - set(config.keys()))
              == len(self._manager_names) - 1):
            # data run found in config
            man_name = tuple(
                self._manager_names - (self._manager_names - set(config.keys()))
            )[0]
            config = config[man_name]

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

    def _validate_config(self, config):
        return config

    def _validate_motion_group(self, config):
        ...

    def link_motion_group(self, mg, index):
        ...



class Manager(BaseActor):
    def __init__(
        self,
        config: Union[str, Dict[str, Any]],
        *,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
    ):
        ...

