"""
Module for functionality focused around the
`~bapsf_motion.actors.axis_.Axis` actor class.
"""
__all__ = ["Axis"]
__actors__ = ["Axis"]

import asyncio
import logging

from typing import Any, Dict

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.motor_ import Motor
from bapsf_motion.utils import units as u


class Axis(BaseActor):
    """
    The `Axis` actor is the next level actor above the |Motor| actor.
    This actor is ignorant of how it is siturated in a probe drive, but
    is fully aware of the entire physical axis it defines.  This actor
    operates in physical units and will handle all the necessary unit
    converstion to communicate with the |Motor| actor.

    Parameters
    ----------
    ip: str
        IPv4 address for the motor driving the axis

    units: str
        Physical units the axis operates in (e.g. ``'cm'``)

    units_per_rev: float
        The number of ``units`` traversed per motor revolution.

    name: str
        Name the axis.  (DEFAULT: ``'Axis'``)

    logger: `~logging.Logger`, optional
        An instance of `~logging.Logger` that the Actor will record
        events and status updates to.  If `None`, then a logger will
        automatically be generated. (DEFUALT: `None`)

    loop: `asyncio.AbstractEventLoop`, optional
        Instance of an `asyncio` `event loop`_. Communication with the
        motor will happen primaritly through the evenet loop.  If
        `None`, then an `event loop`_ will be auto-generated.
        (DEFAULT: `None`)

    auto_run: bool, optional
        If `True`, then the `event loop`_ will be placed in a separate
        thread and started.  This is all done via the :meth:`run`
        method. (DEFAULT: `False`)

    Examples
    --------

    >>> from bapsf_motion.actors import Axis
    >>> import logging
    >>> import sys
    >>> logging.basicConfig(stream=sys.stdout, level=logging.NOTSET)
    >>> ax = Axis(
    ...     ip="192.168.6.104",
    ...     units="cm",
    ...     units_per_rev=0.1*2.54,  # acme rod with .1 in pitch
    ...     name="WALL-E",
    ...     auto_run=True,
    ... )

    """
    # TODO: better handle naming of the Axis and child Motor

    def __init__(
        self,
        *,
        ip: str,
        units: str,
        units_per_rev: float,
        name: str = "Axis",
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
    ):
        super().__init__(logger=logger, name=name)

        self._init_instance_attrs()
        self.motor = Motor(
            ip=ip,
            name="motor",
            logger=self.logger,
            loop=loop,
            auto_run=False,
        )

        # TODO: update units so inches can be used
        self._units = u.Unit(units)
        self._units_per_rev = units_per_rev * self._units / u.rev

        if auto_run:
            self.run()

    def _init_instance_attrs(self):
        """Initialize the class instance attributes."""
        self.motor = None
        self._units = None
        self._units_per_rev = None

    def run(self):
        """
        Activate the `asyncio` `event loop`_.   If the event loop is
        running, then nothing happens.  Otherwise, the event loop is
        placed in a separate thread and set to
        `~asyncio.loop.run_forever`.
        """
        self.motor.run()

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
        self.motor.stop_running(delay_loop_stop=delay_loop_stop)

    @property
    def config(self) -> Dict[str, Any]:
        """Dictionary of the axis configuration parameters."""
        _config = {
            "name": self.name,
            "ip": self.motor.ip,
            "units": str(self.units),
            "units_per_rev": self.units_per_rev.value.item()
        }
        return _config

    @property
    def is_moving(self) -> bool:
        """
        `True` or `False` indicating if the axis is currently moving.
        """
        return self.motor.is_moving

    @property
    def position(self):
        """
        Current axis position in units defined by the :attr:`units`
        attribute.
        """
        pos = self.motor.position
        return pos.to(self.units, equivalencies=self.equivalencies)

    @property
    def steps_per_rev(self):
        """Number of motor steps for a full revolution."""
        return self.motor.steps_per_rev

    @property
    def units(self) -> u.Unit:
        """
        The unit of measure for the `Axis` physical parameters like
        position, speed, etc.
        """
        return self._units

    @units.setter
    def units(self, new_units: u.Unit):
        """Set the units of measure."""
        if self.units.physical_type != new_units.physical_type:
            raise ValueError

        self._units_per_rev = self.units_per_rev.to(new_units / u.rev)
        self._units = new_units

    @property
    def units_per_rev(self) -> u.Quantity:
        """
        The number of units (:attr:`units`) translated per full
        revolution of the motor (:attr:`motor`).
        """
        return self._units_per_rev

    @property
    def equivalencies(self):
        """
        List of unit equivalencies to convert back-and-forth between
        the axis physical units and the motor units.
        """
        steps_per_rev = self.steps_per_rev.value
        units_per_rev = self.units_per_rev.value

        equivs = [
            (
                u.rev,
                u.steps,
                lambda x: x * steps_per_rev,
                lambda x: x / steps_per_rev,
            ),
            (
                u.rev,
                self.units,
                lambda x: x * units_per_rev,
                lambda x: x / units_per_rev,
            ),
            (
                u.steps,
                self.units,
                lambda x: x * units_per_rev / steps_per_rev,
                lambda x: x * steps_per_rev / units_per_rev,
            ),
        ]
        for equiv in equivs.copy():
            equivs.extend(
                [
                    (equiv[0] / u.s, equiv[1] / u.s, equiv[2], equiv[3]),
                    (equiv[0] / u.s / u.s, equiv[1] / u.s / u.s, equiv[2], equiv[3]),
                ]
            )

        return equivs

    @property
    def conversion_pairs(self):
        """
        List of conversion pairs between motor units and physical
        units.  For example, ``[(u.steps, self.units), ...]``.
        """
        return [
            (u.steps, self.units),
            (u.steps / u.s, self.units / u.s),
            (u.steps / u.s / u.s, self.units / u.s / u.s),
            (u.rev / u.s, self.units / u.s),
            (u.rev / u.s / u.s, self.units / u.s / u.s),
        ]

    def send_command(self, command, *args):
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
        """
        cmd_entry = self.motor._commands[command]
        motor_unit = cmd_entry["units"]  # type: u.Unit

        # TODO: put this into a separate convert() method that can handle both
        #       the send and recv unit conversion
        if motor_unit is not None and len(args):
            axis_unit = None
            for motor_u, axis_u in self.conversion_pairs:
                if motor_unit == motor_u:
                    axis_unit = axis_u
                    break

            if axis_unit is not None:
                args = list(args)
                args[0] = args[0] * axis_unit.to(
                    motor_unit, equivalencies=self.equivalencies
                )

        rtn = self.motor.send_command(command, *args)

        # TODO: see detailing todo above
        if hasattr(rtn, "unit"):
            axis_unit = None
            for motor_u, axis_u in self.conversion_pairs:
                if rtn.unit == motor_u:
                    axis_unit = axis_u
                    break

            if axis_unit is not None:
                rtn = rtn.to(axis_unit, equivalencies=self.equivalencies)

        return rtn

    def move_to(self, *args):
        """
        Quick access command for ``send_command("move_to", *args)``.
        """
        return self.send_command("move_to", *args)

    def stop(self):
        """
        Quick access command for ``send_command("stop")``.
        """
        # not sending STOP command through send_command() since using
        # motor.stop() should result in faster execution
        return self.motor.stop()
