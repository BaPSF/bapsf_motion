"""
Module for functionality focused around the
`~bapsf_motion.actors.manager_.Manager` actor class.
"""

__all__ = ["RunManager", "RunManagerConfig"]
__actors__ = ["RunManager"]

import logging

from collections import UserDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

from bapsf_motion.actors.base import EventActor
from bapsf_motion.actors.motion_group_ import (
    MotionGroup,
    MotionGroupConfig,
    handle_user_metadata
)
from bapsf_motion.utils import toml, _deepcopy_dict


class RunManagerConfig(UserDict):
    _manager_names = {"run"}
    _mg_names = MotionGroupConfig._mg_names
    _required_metadata = {"run", "name"}

    def __init__(
        self,
        config: Union[str, Dict[str, Any], "RunManagerConfig", Path],
        logger: logging.Logger = None,
    ):
        self.logger = logging.getLogger("RM_config") if logger is None else logger

        # Make sure config is the right type, and is a dict by the
        # end of ths code block
        if isinstance(config, RunManagerConfig):
            # This could happen when creating a new RunManger from an
            # old / terminated RunManager
            #
            # we need to deep copy to avoid passing around actor objects
            # from the old config
            config = _deepcopy_dict(config)
        elif isinstance(config, str):
            # could be path to TOML file or a TOML like string
            if Path(config).exists():
                with open(config, "rb") as f:
                    config = toml.load(f)
            else:
                config = toml.loads(config)
        elif isinstance(config, Path):
            # path to TOML file
            with open(config, "rb") as f:
                config = toml.load(f)
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
            self.logger.warning(
                "Run configuration is missing a unique name for the run, "
                f"naming the configuration '{rname}'."
            )
            # warnings.warn(
            #     "Run configuration is missing a unique name for the run, "
            #     f"naming the configuration '{rname}'",
            #     ConfigurationWarning,
            # )
            config["name"] = rname

        config["date"] = date

        # Are there motion groups
        mg_names_not_in_config = self._mg_names - set(config)
        if len(mg_names_not_in_config) == len(self._mg_names):
            self.logger.error(
                "ValueError: The run configuration has no defined motion groups, "
                "there needs to be at least one motion group."
            )
            config["motion_group"] = {}

            return config

        # collect possible motion group configurations
        mg_names_in_config = self._mg_names - mg_names_not_in_config
        collected_mg_configs = {}
        for mg_name in mg_names_in_config:
            mg_config = config.pop(mg_name)

            if not isinstance(mg_config, (dict, UserDict)):
                self.logger.error(
                    f"TypeError: Expected a dictionary for the motion group "
                    f"configuration, but got type {type(mg_config)}."
                )
                continue

            if "name" in mg_config:
                # assume only one motion group is defined
                index = len(collected_mg_configs)
                collected_mg_configs[index] = mg_config
                continue

            for mgc in mg_config.values():

                if not isinstance(mgc, (dict, UserDict)):
                    self.logger.error(
                        f"TypeError: Expected a dictionary for the motion group "
                        f"configuration, but got type {type(mg_config)}."
                    )
                    continue

                index = len(collected_mg_configs)
                collected_mg_configs[index] = mgc

        config = self._handle_user_meta(config, {"name", "date"})
        config["motion_group"] = {}

        for key, val in collected_mg_configs.items():
            config["motion_group"][key] = MotionGroupConfig(val)

        config = self._validate_motion_group_names(config)
        config = self._validate_drive_ips(config)

        return config

    def _validate_motion_group_names(self, config: Dict[str, Any]):
        mg_config_names = [val["name"] for val in config["motion_group"].values()]
        if len(set(mg_config_names)) != len(mg_config_names):
            duplicates = []
            for name in set(mg_config_names):
                count = mg_config_names.count(name)
                if count != 1:
                    duplicates.append(name)

            self.logger.error(
                f"ValueError: All configured motion groups must have unique names, "
                f"found duplicates for {duplicates}.  Remove motion groups with "
                f"duplicate names."
            )

            new_mg_config = {}
            for key, val in config["motion_group"].items():
                if val["name"] in duplicates:
                    continue

                new_mg_config[key] = val

            config["motion_group"] = new_mg_config

        return config

    def _validate_drive_ips(self, config: Dict[str, Any]):
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

            self.logger.error(
                f"ValueError: All configured motion groups must have unique motor IP "
                f"addresses, found  duplicates for {duplicates}.  Removing "
                f"motion groups with shared IPs."
            )

            new_mg_configs = {}
            for key, val in config["motion_group"].items():
                dr = val["drive"]

                remove = False
                for ax in dr["axes"].values():
                    if ax["ip"] in duplicates:
                        remove = True
                        break

                if not remove:
                    new_mg_configs[key] = val
                else:
                    remove = False

        return config

    def _handle_user_meta(self, config: Dict[str, Any], req_meta: set) -> Dict[str, Any]:
        """
        If a user specifies metadata that is not required by a specific
        configuration component, then collect all the metadata and
        store it under the 'user' key.  Return the modified dictionary.
        """
        return handle_user_metadata(
            config=config, req_meta=req_meta, logger=self.logger)

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

    def unlink_motion_group(self, key):
        """Unlink and remove motion group from the configuration."""
        if self._mgs is not None:
            self._mgs.pop(key, None)

        if key in self["motion_group"]:
            del self["motion_group"][key]

    @property
    def as_toml_string(self) -> str:
        return toml.as_toml_string({"run": self})

    def update_run_name(self, name: str):
        if not isinstance(name, str):
            self.logger.warning(
                f"TypeError:  Attempted changing run name but got type "
                f"{type(name)}, expected type string."
            )

        self["name"] = name


class RunManager(EventActor):
    def __init__(
        self,
        config: Union[str, Dict[str, Any], RunManagerConfig, Path],
        *,
        # logger: logging.Logger = None,
        # loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
        build_mode: bool = False,
        parent: Optional["EventActor"] = None,
    ):
        self._mgs = None
        self._config = None

        logger = logging.getLogger("RM")
        super().__init__(
            logger=logger,
            auto_run=False,
            parent=parent
        )
        self.name = "RM"

        try:
            config = RunManagerConfig(config, logger=self.logger)
        except (TypeError, ValueError) as err:
            if not build_mode:
                raise err

            self.logger.error(f"{err.__class_.__name__}: {err}")

            config = RunManagerConfig(
                config={"name": "Run Build"},
                logger=self.logger,
            )
            auto_run = False

        self._config = config

        for key, mgc in self._config["motion_group"].items():
            self._raw_add_motion_group(mgc, key)
        
        self.run(auto_run=auto_run)
    
    def _configure_before_run(self):
        return 
    
    def _initialize_tasks(self):
        return

    def run(self, auto_run=True):
        super().run(auto_run=auto_run)

        if self.mgs is None or not self.mgs:
            return

        for mg in self.mgs.values():
            if not mg.terminated:
                mg.run()
    
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
            auto_run=False,
            parent=self,
        )

    @property
    def is_moving(self):
        return any([mg.is_moving for mg in self.mgs.values()])

    def validate_motion_group(
        self,
        mg_config: Union[Dict[str, Any], MotionGroup, MotionGroupConfig],
        identifier: Union[str, int] = None,
    ) -> bool:

        if isinstance(mg_config, MotionGroup):
            mg = mg_config
            mg_config = mg.config
        elif isinstance(mg_config, MotionGroupConfig):
            pass
        else:
            try:
                mg_config = MotionGroupConfig(mg_config)
            except (ValueError, TypeError):
                return False

        if identifier is None:
            identifier = len(self.mgs)

        new_rm_config = _deepcopy_dict(self.config)
        new_rm_config["motion_group"][identifier] = mg_config

        new_rm_config = RunManagerConfig(new_rm_config)

        return identifier in new_rm_config["motion_group"]

    def _raw_add_motion_group(self, config, identifier):
        """A direct add of the motion group without any validation."""
        if isinstance(config, MotionGroup):
            mg_config = config.config
            config.terminate(delay_loop_stop=True)
            config = mg_config

        mg = self._spawn_motion_group(config)
        self.mgs[identifier] = mg
        self.config.link_motion_group(mg, identifier)

    def add_motion_group(
        self,
        config: Union[Dict[str, Any], MotionGroupConfig, MotionGroup],
        identifier: Union[str, int] = None,
    ):
        if identifier is None:
            identifier = len(self.mgs)

        valid = self.validate_motion_group(config, identifier)

        if valid:
            self.remove_motion_group(identifier)
            self._raw_add_motion_group(config, identifier)

    def remove_motion_group(self, identifier: Union[str, int]):
        self.config.unlink_motion_group(identifier)

        if identifier in self.mgs:
            self.mgs[identifier].terminate(delay_loop_stop=True)
            del self.mgs[identifier]

    def get_motion_group(self, identifier: Union[str, int]):
        return self.mgs[identifier]

    def pop_motion_group(self, identifier: Union[str, int]):
        mg = self.mgs.pop(identifier, None)
        self.config.unlink_motion_group(identifier)

        return mg
