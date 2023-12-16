"""
Module for functionality focused around the
`~bapsf_motion.actors.manager_.Manager` actor class.
"""

__all__ = ["RunManager", "RunManagerConfig"]
__actors__ = ["RunManager"]

import asyncio
import logging
import warnings

from collections import UserDict
from datetime import datetime, timezone
from typing import Any, Dict, Union

from bapsf_motion.actors.base import EventActor
from bapsf_motion.actors.motion_group_ import MotionGroup, MotionGroupConfig
from bapsf_motion.utils import toml
from bapsf_motion.utils.exceptions import ConfigurationWarning


class RunManagerConfig(UserDict):
    _manager_names = {"run"}
    _mg_names = MotionGroupConfig._mg_names
    _required_metadata = {"run", "name"}

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
        self._mgs = None  # type: Union[None, Dict[Union[str, int], MotionGroup]]

        super().__init__(config)
        self._data = self.data

    @property
    def data(self):
        """
        A real dictionary used to store the contents of
        `RunManagerConfig`.
        """
        if self._mgs is not None:
            for key, mg in self._mgs.items():
                self._data["motion_group"][key] = mg.config

        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def _validate_config(self, config):
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M %Z')
        if "name" not in config:
            rname = f"run [{date}]"
            warnings.warn(
                "Run configuration is missing a unique name for the run, "
                f"naming the configuration '{rname}'",
                ConfigurationWarning,
            )
            config["name"] = rname

        config["date"] = date

        # Are there motion groups
        mg_names_not_in_config = self._mg_names - set(config)
        if len(mg_names_not_in_config) == len(self._mg_names):
            raise ValueError(
                "The run configuration has no defined motion groups, "
                "there needs to be at least one motion group."
            )

        # collect possible motion group configurations
        mg_names_in_config = self._mg_names - mg_names_not_in_config
        collected_mg_configs = {}
        for mg_name in mg_names_in_config:
            mg_config = config.pop(mg_name)

            if not isinstance(mg_config, dict):
                raise TypeError(
                    "Expected a dictionary for the motion group configuration,"
                    f" but got type {type(mg_config)}."
                )

            if "name" in mg_config:
                # assume only one motion group is defined
                index = len(collected_mg_configs)
                collected_mg_configs[index] = mg_config
                continue

            for mgc in mg_config.values():

                if not isinstance(mgc, dict):
                    raise TypeError(
                        "Expected a dictionary for the motion group configuration,"
                        f" but got type {type(mg_config)}."
                    )

                index = len(collected_mg_configs)
                collected_mg_configs[index] = mgc

        config = self._handle_user_meta(config, {"name", "date"})
        config["motion_group"] = {}

        for key, val in collected_mg_configs.items():
            config["motion_group"][key] = MotionGroupConfig(val)

        self._validate_motion_group_names(config)
        self._validate_drive_ips(config)

        return config

    @staticmethod
    def _validate_motion_group_names(config: Dict[str, Any]):
        mg_config_names = [val["name"] for val in config["motion_group"].values()]
        if len(set(mg_config_names)) != len(mg_config_names):
            duplicates = []
            for name in set(mg_config_names):
                count = mg_config_names.count(name)
                if count != 1:
                    duplicates.append(name)

            raise ValueError(
                "All configured motion groups must have unique names, found"
                f" duplicates for {duplicates}."
            )

    @staticmethod
    def _validate_drive_ips(config: Dict[str, Any]):
        drive_configs = [val["drive"] for val in config["motion_group"].values()]
        drive_ips = []
        for dr in drive_configs:
            ips = [val["ip"] for val in dr["axes"].values()]
            drive_ips.extend(ips)

        if len(set(drive_ips)) != len(drive_ips):
            duplicates = []
            for ip in set(drive_ips):
                count = drive_ips.count(ip)
                if count != 1:
                    duplicates.append(ip)

            raise ValueError(
                "All configured motion groups must have unique motor IP "
                f"addresses, found  duplicates for {duplicates}."
            )

    @staticmethod
    def _handle_user_meta(config: Dict[str, Any], req_meta: set) -> Dict[str, Any]:
        """
        If a user specifies metadata that is not required by a specific
        configuration component, then collect all the metadata and
        store it under the 'user' key.  Return the modified dictionary.
        """
        return MotionGroupConfig._handle_user_meta(config, req_meta)

    def link_motion_group(self, mg, key):
        if not isinstance(mg, MotionGroup):
            raise TypeError(
                f"For argument 'mg' expected type {MotionGroup}, but got "
                f"type {type(mg)}."
            )

        if self._mgs is None:
            self._mgs = {key: mg}
        else:
            self._mgs[key] = mg

    @property
    def as_toml_string(self):
        def convert_key_to_string(_d):
            _config = {}
            for key, value in _d.items():
                if isinstance(value, (dict, UserDict)):
                    value = convert_key_to_string(value)

                if not isinstance(key, str):
                    key = f"{key}"

                _config[key] = value

            return _config

        return "[run]\n" + toml.dumps(convert_key_to_string(self))


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

        for key, mgc in self._config["motion_group"].items():
            mg = self._spawn_motion_group(mgc)
            self.mgs[key] = mg
            self._config.link_motion_group(self.mgs[key], key=key)
        
        self.run(auto_run=auto_run)
    
    def _configure_before_run(self):
        return 
    
    def _initialize_tasks(self):
        return 
    
    @property
    def mgs(self) -> Dict[Union[str, int], MotionGroup]:
        if self._mgs is None:
            self._mgs = {}
        
        return self._mgs

    @property
    def config(self) -> RunManagerConfig:
        return self._config
    config.__doc__ = EventActor.config.__doc__
    
    def terminate(self, delay_loop_stop=False):
        for mg in self.mgs.values():
            mg.terminate(delay_loop_stop=True)
        super().terminate(delay_loop_stop=delay_loop_stop)

    def _spawn_motion_group(self, config: Dict[str, Any]) -> MotionGroup:
        return MotionGroup(
            config=config,
            logger=self.logger,
            loop=self.loop,
            auto_run=False
        )

    @property
    def is_moving(self):
        return any([mg.is_moving for mg in self.mgs.values()])
