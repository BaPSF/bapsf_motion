"""
Module for functionality focused around the
`~bapsf_motion.actors.manager_.Manager` actor class.
"""

__all__ = ["RunManager", "RunManagerConfig"]
__actors__ = ["RunManager"]

import asyncio
import logging

from collections import UserDict
from typing import Any, Dict, List, Union

from bapsf_motion.actors.base import EventActor
from bapsf_motion.actors.motion_group_ import MotionGroup, MotionGroupConfig
from bapsf_motion.utils import toml


class RunManagerConfig(UserDict):
    _manager_names = {"run"}

    def __init__(self, config: Union[str, Dict[str, Any]]):

        # Make sure config is the right type, and is a dict by the
        # end of ths code block
        if isinstance(config, RunManagerConfig):
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


class RunManager(EventActor):
    def __init__(
        self,
        config: Union[str, Dict[str, Any]],
        *,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
    ):
        config = RunManagerConfig(config)
        self._mgs = None

        super().__init__(
            name=config["name"],
            logger=logger,
            loop=loop,
            auto_run=False,
        )

        self._config = config

        # for mgc in mgcs:
        #     mg = self._spawn_motion_group()
        #     self.mgs.append(mg)
        #     self._config.link_motion_group(self.mgs[-1])
        
        self.run(auto_run=auto_run)
    
    def _configure_before_run(self):
        return 
    
    def _initialize_tasks(self):
        return 
    
    @property
    def mgs(self) -> List[MotionGroup]:
        if self._mgs is None:
            self._mgs = []
        
        return self._mgs

    @property
    def config(self):
        return self._config
    config.__doc__ = EventActor.config.__doc__
    
    def terminate(self, delay_loop_stop=False):
        for mg in self.mgs:
            mg.terminate(delay_loop_stop=True)
        super().terminate(delay_loop_stop=delay_loop_stop)

    def _spawn_motion_group(self, config: Dict[str, Any]) -> MotionGroup:
        ...
