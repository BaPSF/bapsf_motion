"""
Module for functionality focused around the
`~bapsf_motion.actors.drive_.Drive` actor class.
"""
__all__ = ["Drive"]
__actors__ = ["Drive"]

import astropy.units as u
import asyncio
import logging
import threading

from typing import Any, Dict, List, Optional, Tuple

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.axis_ import Axis


class Drive(BaseActor):
    """
    The `Drive` actor is the next level actor above the |Axis| actor.
    This actor is ignorant of how the probe drive is implemented in
    the physical space, but it is fully aware of the axes that make up
    the probe drive.  The axes are ordered, but the actor has no clue
    how these axes are oriented in the physical space.  This actor
    operates in phsical units of the axes.

    Parameters
    ----------
    axes: List[Dict[str, Any]]
        A `list` or `tuple` of `dict` elements.  Each dictionary element
        contains the input arguments need to create an |Axis| instance.
        The order of the list defines the order of the axes, i.e.
        element index 0 defines axis 0.

    name: str, optional
        Name the drive.  If `None`, then a name will be auto-generated.

    logger: `~logging.Logger`, optional
        An instance of `~logging.Logger` that the Actor will record
        events and status updates to.  If `None`, then a logger will
        automatically be generated. (DEFUALT: `None`)

    loop: `asyncio.AbstractEventLoop`, optional
        Instance of an `asyncio` `event loop`_. Communication with all
        the axes will happen primaritly through the evenet loop.  If
        `None`, then an `event loop`_ will be auto-generated.
        (DEFAULT: `None`)

    auto_run: bool, optional
        If `True`, then the `event loop`_ will be placed in a separate
        thread and started.  This is all done via the :meth:`run`
        method. (DEFAULT: `False`)

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
        axes: List[Dict[str, Any]],
        name: str = None,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
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
        """Initialize the class instance attributes."""
        self._axes = None
        self._loop = None
        self._thread = None

    def _validate_axes(self, settings: List[Dict[str, Any]]) -> Tuple[Dict[str, Any]]:
        """
        Validate the |Axis| arguments for all axes defined in
        ``settings``.

        Restrictions:
        - All IPv4 addresses must be unique.
        - All |Axis| names must be unique.
        """
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
        """Validate the |Axis| arguments defined in ``settings``."""
        # TODO: create warnings for logger, loop, and auto_run since
        #       this class overrides in inputs of thos
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

    def _spawn_axis(self, settings: Dict[str, Any]) -> Axis:
        """
        Initialize an |Axis| with the input arguments defined in the
        ``settings`` dictionary.  The key-value pairs defined in
        ``settings`` can only match those of |Axis| input arguments.
        """
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
    def config(self) -> Dict[str, Any]:
        """The |Drive| configuration dictionary."""
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
    def is_moving(self) -> bool:
        """
        `True` if any axis in the |Drive| is moving, otherwise `False`.
        """
        return any(ax.is_moving for ax in self.axes)

    @property
    def axes(self) -> List[Axis]:
        """List of the drive's axis instances."""
        return list(self._axes)

    @property
    def naxes(self) -> int:
        """Number of axes defined in the |Drive|."""
        return len(self.axes)

    @property
    def anames(self) -> Tuple[str]:
        """Tuple of the names of the defined axes."""
        return tuple(ax.name for ax in self.axes)

    @property
    def position(self) -> u.Quantity:
        """The :attr:`naxes`-D position of the probe drive."""
        # TODO: thiS needs to return drive units instead of axis units
        # TODO: handle case where someone could have config different units for each axis
        pos = []
        for ax in self.axes:
            pos.append(ax.position.value)

        return pos * self.axes[0].units

    def run(self):
        """
        Activate the `asyncio` `event loop`_.   If the event loop is
        running, then nothing happens.  Otherwise, the event loop is
        placed in a separate thread and set to
        `~asyncio.loop.run_forever`.
        """
        if self._loop.is_running():
            return

        self._thread = threading.Thread(target=self._loop.run_forever)
        self._thread.start()

    def stop_running(self, delay_loop_stop=False):
        """
        Stop the actor's `event loop`_\ .  All actor tasks will be
        cancelled, the connection to the motor will be shutdown, and
        the event loop will be stopped.

        Parameters
        ----------
        delay_loop_stop: bool
            If `True`, then do NOT stop the `event loop`_\ .  In this
            case it is assumed the calling functionality is managing
            additional tasks in the event loop, and it is up to that
            functionality to stop the loop.  (DEFAULT: `False`)

        """
        for ax in self._axes:
            ax.stop_running(delay_loop_stop=True)

        if delay_loop_stop:
            return

        self._loop.call_soon_threadsafe(self._loop.stop)

    def setup_event_loop(self, loop):
        """
        Set up the `asyncio` `event loop`_.  If the given loop is not an
        instance of `~asyncio.AbstractEventLoop`, then a new loop will
        be created.  The `event loop`_ is, then populated with the
        relevant actor tasks.

        Parameters
        ----------
        loop: `asyncio.AbstractEventLoop`
            `asyncio` `event loop`_ for the actor's tasks

        """
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

    def send_command(self, command, *args, axis: Optional[int] = None):
        """
        Send ``command`` to the motor, and receive its response.  If the
        `event loop`_ is running, then the command will be sent as
        a threadsafe coroutine_ in the loop.  Otherwise, the command
        will be sent directly to the motor.

        Parameters
        ----------
        command: str
            The desired command to be sent to the motor.
        *args:
            Any arguments to the ``command`` that will be sent with the
            motor command.
        axis: int, optional
            Axis index the comment is directed to.  If `None`, then the
            command is sent to all axes. (DEFAULT: `NONE`)
        """
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

    def move_to(self, pos, axis: Optional[int] = None):
        """
        Move the drive to a specified location.

        Parameters
        ----------
        pos: :term:`array_like`
            Position (in axis represented units) for the drive to move
            to.  Can be singled valued if just moving an individual
            axes, or the same lengths as :attr:`naxes` if moving the
            whole probe drive.
        axis: int, optional
            Axis index for the axis to be moved.  If `None`, then it
            is assumed all axes need to be moved and ``pos`` has the
            same length as :attr:`naxes`.  (DEFAULT: `None`)
        """
        # TODO: should I sent these commands through
        #       Drive.send_command() instead?
        # TODO: Is there a way to handle axes with different units
        # TODO: Should pos be allows to be an astropy Quantity

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
        """Stop all axes from moving."""
        # TODO: should I really be construct a return here?
        # TODO: is there a quicker/more efficient way of stopping the motors?

        rtn = []
        for ax in self.axes:
            _rtn = ax.stop()
            rtn.append(_rtn)

        return rtn

    def sel(self, aname):
        """Select an axis index from a given axis name ``aname``."""
        index = self.anames.index(aname)
        return self.axes[index]
