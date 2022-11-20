import astropy.units as u
import asyncio
import threading

from typing import Any, Dict, List, Tuple

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
        ...     ],
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
        all_anames = []
        for ii, axis in enumerate(settings):
            axis = self._validate_axis(axis)
            if "name" not in axis:
                axis["name"] = f"ax{ii}"

            conditioned_settings.append(axis)
            all_ips.append(axis["ip"])
            all_anames.append(axis["name"])

        # TODO: update this so https://, not using https (or http), or a port
        #       does result in False unique entries
        if len(set(all_ips)) != len(all_ips):
            raise ValueError(
                f"All specified axes must have unique IPs, duplicate "
                f"IPs found."
            )

        if len(set(all_anames)) != len(all_anames):
            raise ValueError(
                f"All specified axes must have unique names, duplicate "
                f"axis names found."
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
    def config(self):
        _config = {
            "name": self.name,
            "axes": {},
        }

        for ax in self.axes:
            for key, val in ax.config.items():
                if key not in _config["axes"]:
                    _config["axes"][key] = [val]
                else:
                    _config["axes"][key].append(val)

        return _config

    @property
    def is_moving(self):
        return any(ax.is_moving for ax in self.axes)

    @property
    def axes(self) -> List[Axis]:
        return list(self._axes)

    @property
    def naxes(self):
        return len(self.axes)

    @property
    def anames(self):
        return (ax.name for ax in self.axes)

    @property
    def position(self) -> u.Quantity:
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
        if axis is None:
            send_to = self.axes
        elif axis in range(len(self.axes)):
            send_to = [self.axes[int(axis)]]
        else:
            raise ValueError(
                f"Value for keyword 'axis' is unrecognized.  Got {axis} and"
                f" expected None or in in range({len(self.axes)})."
            )

        if len(send_to) == 1:
            rtn = send_to[0].send_command(command, *args)
            return rtn

        rtn = []
        for ii, ax in enumerate(send_to):
            ax_args = (args[ii],) if len(args) else args
            _rtn = ax.send_command(command, *ax_args)
            rtn.append(_rtn)

        return rtn

    def move_to(self, pos, axis=None):
        # TODO: should I sent these commands through
        #       Drive.send_command() instead?

        if axis is None and len(pos) != len(self.axes):
            raise ValueError(
                f"Keyword `pos` must be a tuple of equal length to the "
                f"number drive axes, got {len(pos)} and expected "
                f"{len(self.axes)}."
            )
        elif axis is not None and axis not in range(len(self.axes)):
            raise ValueError(
                f"Keyword `axis` is supposed to be an int in "
                f"range({len(self.axes)}), got {axis}."
            )
        elif axis is not None and not isinstance(pos, (list, tuple)):
            pos = [pos]
        elif axis is not None and len(pos) != 1:
            raise ValueError(
                f"When keyword `axis` is used the specified position "
                f"`pos` must be of length one, got lengths {len(pos)}."
            )

        move_ax = self.axes if axis is None else [self.axes[axis]]
        rtn = []
        for p, ax in zip(pos, move_ax):
            _rtn = ax.move_to(p)
            rtn.append(_rtn)

        return rtn

    def stop(self):
        # TODO: should I really be construct a return here?
        # TODO: is there a quicker/more efficient way of stopping the motors?

        rtn = []
        for ax in self.axes:
            _rtn = ax.stop()
            rtn.append(_rtn)

        return rtn

    def sel(self, aname):
        index = self.anames.index(aname)
        return self.axes[index]
