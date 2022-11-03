import asyncio
import threading

from typing import Any, Dict, Tuple

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.axis_ import Axis


class Drive(BaseActor):
    """
        Examples
        --------

        >>> from bapsf_motion.actors import Drive
        >>> import logging
        >>> import sys
        >>> logging.basicConfig(stream=sys.stdout, level=logging.NOTSET)
        >>> dr = Drive(
        ...     axes=[
        ...         {"ip": "192.168.6.104", "units": "cm", "units_per_rev": 0.1*2.54},
        ...         {"ip": "192.168.6.103", "units": "cm", "units_per_rev": 0.1*2.54},
        ...     ]
        ...     name="WALL-E",
        ...     auto_run=True,
        ... )

        """

    def __init__(
        self,
        *,
        axes,
        name: str = None,
        logger=None,
        loop=None,
        auto_run=False,
    ):
        super().__init__(logger=logger, name=name)

        self._init_instance_variables()
        self.setup_event_loop(loop)
        axes = self._validate_axes(axes)

        axis_objs = []
        for axis in axes:
            ax = self._spawn_axis(axis)
            axis_objs.append(ax)

        self._axes = tuple(axis_objs)

        if auto_run:
            self.run()

    def _init_instance_variables(self):
        self._axes = None
        self._loop = None
        self._thread = None

    def _validate_axes(self, settings: Tuple[Dict[str, Any]]) -> Tuple[Dict[str, Any]]:

        conditioned_settings = []
        all_ips = []
        for ii, axis in enumerate(settings):
            axis = self._validate_axis(axis)
            if "name" not in axis:
                axis["name"] = f"ax{ii}"

            conditioned_settings.append(axis)
            all_ips.append(axis["ip"])

        # TODO: update this so https://, not using https (or http), or a port
        #       does result in False unique entries
        if len(set(all_ips)) != len(all_ips):
            raise ValueError(
                f"All specified axes must have unique IPs, duplicate IPs found."
            )

        return tuple(conditioned_settings)

    @staticmethod
    def _validate_axis(settings: Dict[str, Any]) -> Dict[str, Any]:
        required_parameters = {"ip": str, "units": str, "units_per_rev": float}

        if not isinstance(settings, dict):
            raise TypeError(
                f"Axis settings needs to be a dictionary, got type {type(settings)}."
            )
        elif set(required_parameters) - set(settings):
            raise ValueError(
                f"Not all required axis settings are defined, missing "
                f"{set(required_parameters) - set(settings)}."
            )

        for key, value in required_parameters.items():
            if not isinstance(settings[key], value):
                raise ValueError(
                    f"For axis setting '{key}' expected type {value}, got "
                    f"type {type(settings[key])}."
                )

        return settings

    def _spawn_axis(self, settings):
        ax = Axis(
            **{
                **settings,
                "logger": self.logger,
                "loop": self._loop,
                "auto_run": False,
            },
        )

        return ax

    @property
    def is_moving(self):
        return any(ax.is_moving for ax in self.axes)

    @property
    def axes(self):
        return self._axes

    @property
    def position(self):
        # TODO: thiS needs to return drive units instead of axis units
        # TODO: handle case where someone could have config different units for each axis
        pos = []
        for ax in self.axes:
            pos.append(ax.position.value)

        return pos * self.axes[0].units

    def run(self):
        if self._loop.is_running():
            return

        self._thread = threading.Thread(target=self._loop.run_forever)
        self._thread.start()

    def stop_running(self, delay_loop_stop=False):
        for ax in self._axes:
            ax.stop_running(delay_loop_stop=True)

        if delay_loop_stop:
            return

        self._loop.call_soon_threadsafe(self._loop.stop)

    def setup_event_loop(self, loop):
        # 1. loop is given and running
        #    - store loop
        #    - add tasks
        # 2. loop is given and not running
        #    - store loop
        #    - add tasks
        # 3. loop is NOT given
        #    - create new loop
        #    - store loop
        #    - add tasks
        # get a valid event loop
        if loop is None:
            loop = asyncio.new_event_loop()
        elif not isinstance(loop, asyncio.events.AbstractEventLoop):
            self.logger.warning(
                "Given asyncio event is not valid.  Creating a new event loop to use."
            )
            loop = asyncio.new_event_loop()
        self._loop = loop

    def send_command(self, command, *args, axis=None):
        ...

    def move_to(self, *args):
        ...

    def stop(self):
        ...
