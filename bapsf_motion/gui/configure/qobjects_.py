"""
This module contains custom `QObjects` that are used withing the
`bapsf_motion.gui.configure` framework.
"""

__all__ = ["RunManagerObject"]

import logging

from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from typing import Any, Dict

from bapsf_motion.actors import RunManager, RunManagerConfig
from bapsf_motion.gui.configure.helpers import gui_logger


class RunManagerObject(QObject):
    """
    A `QObject` that contains the actual `RunManager` instance and
    defines the supporting operations onto the `RunManger` that the
    rest of `ConfigureGUI` can interact with.
    """

    configChanged = Signal()

    def __init__(
        self,
        config: Path | str | Dict[str, Any] | RunManagerConfig,
        parent: QObject | None = None,
    ):
        super().__init__(parent=parent)

        # Initialize Attributes
        self._logger = logging.getLogger(f"{gui_logger.name}.RMO")

        self._rm = None
        self.replace_rm(config=config)
        if not isinstance(self._rm, RunManager):
            message = f"The specified RunManager configuration is not valid.\n {config}"
            self.logger.error(message)
            raise ValueError(message)

        self._connect_signals()

    def _connect_signals(self): ...

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def rm(self) -> RunManager:
        return self._rm

    @rm.setter
    def rm(self, new_rm: RunManager):
        if not isinstance(new_rm, RunManager):
            return

        if isinstance(self._rm, RunManager):
            self._rm.terminate(disconnect_signals=True)

        self._rm = new_rm

    def replace_rm(self, config):
        if isinstance(self.rm, RunManager):
            self.rm.terminate(disconnect_signals=True)

        self.logger.info(f"Replacing the run manager with new config: {config}.")
        _rm = RunManager(config=config, auto_run=True, build_mode=True)

        _remove = []
        for key, mg in _rm.mgs.items():
            if mg.drive.naxes != 2:
                self.logger.warning(
                    f"The Configuration GUI currently only supports motion"
                    f" groups with a dimensionality of 2, got {mg.drive.naxes}"
                    f" for motion group '{mg.name}'.  Removing motion group."
                )
                _remove.append(key)
                continue

            if not mg.connected:
                # MotionGroup failed to fully connect on initialization.
                # Terminate the MotionGroup and require the user to go
                # into config mode to remedy the situation.
                #
                mg.terminate(delay_loop_stop=True)

        for key in _remove:
            _rm.remove_motion_group(key)

        self.rm = _rm
        self.configChanged.emit()

    def change_run_name(self, name: str):
        if not isinstance(name, str):
            return

        rm = self.rm
        if not isinstance(rm, RunManager):
            self.replace_rm({"name": name})
            return

        rm.config.update_run_name(name)
        self.configChanged.emit()

    def run(self, auto_run: bool = True, force_run: bool = True):
        rm = self.rm
        if not isinstance(rm, RunManager):
            # No RunManager to restart
            self.logger.warning(
                "Unable to run the RunManger instance.  There is NO instance to run."
            )
            return

        if (
            isinstance(rm, RunManager)
            and not rm.terminated
            and all(mg.connected for mg in rm.mgs.values())
        ):
            # RunManager is still running, no need to restart
            return

        rm.run(auto_run=auto_run, force_run=force_run)

        for mg in rm.mgs.values():
            if not mg.connected:
                # MotionGroup failed to fully re-connect.
                # Terminate the MotionGroup and require the user to go
                # into config mode to remedy the situation.
                #
                mg.terminate(delay_loop_stop=True)

        self.configChanged.emit()

    def add_motion_group(self, index: int, mg_config: Dict[str, Any]):
        index = None if index == -1 else index

        self.logger.info(
            f"Adding MotionGroup to the run: index = '{index}', config = {mg_config}."
        )

        self.rm.add_motion_group(config=mg_config, identifier=index)
        self.configChanged.emit()

    @Slot(str)
    def remove_motion_group(self, identifier: str | int):
        rm = self.rm

        if not isinstance(rm, RunManager):
            return

        if identifier in rm.mgs.keys():
            rm.remove_motion_group(identifier=identifier)
            self.configChanged.emit()
            return

        if isinstance(identifier, int):
            identifier = f"{identifier}"
        elif isinstance(identifier, str):
            try:
                identifier = int(identifier)
            except ValueError:
                return
        else:
            return

        rm.remove_motion_group(identifier=identifier)
        self.configChanged.emit()

    def terminate(
        self,
        delay_loop_stop: bool = False,
        disconnect_signals: bool = False,
    ):
        rm = self.rm
        if not isinstance(rm, RunManager):
            return

        rm.terminate(
            delay_loop_stop=delay_loop_stop,
            disconnect_signals=disconnect_signals,
        )
