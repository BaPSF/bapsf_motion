__all__ = ["Axis"]

import astropy.units as u
import logging

from typing import Dict, Union

from bapsf_motion.actors.motor_ import Motor


class Axis:

    def __init__(
        self,
        *,
        ip: str,
        units: str,
        units_per_rev: float,
        name: str = None,
        logger=None,
        loop=None,
        auto_run=False,
    ):
        self._init_instance_attrs()
        self.setup_logger(logger, "Axis")
        self.motor = Motor(
            ip=ip,
            name=name,
            logger=self.logger,
            loop=loop,
            auto_start=False,
        )

        self._units = u.Unit(units)
        self._units_per_rev = units_per_rev

        if auto_run:
            self.run()

    def _init_instance_attrs(self):
        """Initialize the class instance attributes."""
        self.motor = None
        self._logger = None
        self._name = ""
        self._units = None
        self._units_per_rev = None

    def setup_logger(self, logger, name):
        """Setup logger to track events."""
        log_name = __name__ if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"
            self.name = name
        self._logger = logging.getLogger(log_name)

    def run(self):
        """Start the `asyncio` event loop."""
        self.motor.run()

    def stop_running(self, delay_loop_stop=False):
        """Stop the `asyncio` event loop."""
        self.motor.stop_running(delay_loop_stop=delay_loop_stop)

    @property
    def is_moving(self) -> bool:
        """
        `True` or `False` indicating if the axis is currently moving.
        """
        return self.motor.is_moving

    @property
    def logger(self):
        """Event logger for the class"""
        return self._logger

    @property
    def name(self):
        """Given name for the `Axis` instance."""
        return self._name

    @name.setter
    def name(self, value):
        """Set the given name for the `Axis` instance."""
        self._name = value

    @property
    def position(self):
        """
        Current axis position in units defined by the :attr:`units`
        attribute.
        """
        pos = self.motor.position
        return self.convert_steps_to_units(pos)

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

        conversion = self.units.to(new_units)
        self._units_per_rev = conversion * self.units_per_rev

        self._units = new_units

    @property
    def units_per_rev(self):
        """
        The number of units (:attr:`units`) translated per full
        revolution of the motor (:attr:`motor`).
        """
        return self._units_per_rev

    def conversions(self, command) -> Union[Dict[str, callable], None]:
        if command in ("acceleration", "deceleration", "speed"):
            return {
                "outbound": lambda x: x / self.units_per_rev,
                "inbound": lambda x: round(x * self.units_per_rev, 2),
            }
        elif command in ("move_to", "target_position"):
            return {
                "outbound": self.convert_unit_to_steps,
                "inbound": self.convert_steps_to_units,
            }

    def send_command(self, command, *args):
        conversion = self.conversions(command)
        if conversion is not None and len(args):
            args = list(args)
            args[0] = conversion["outbound"](args[0])

        rtn = self.motor.send_command(command, *args)

        if command is not None and rtn is not None:
            return conversion["inbound"](rtn)

        return rtn

    def move_to(self, *args):
        return self.send_command("move_to", *args)

    def stop(self):
        # not sending STOP command through send_command() since using
        # motor.stop() should result in faster execution
        return self.motor.stop()

    def convert_unit_to_steps(self, value):
        return value * self.steps_per_rev / self.units_per_rev

    def convert_steps_to_units(self, value):
        return round(value * self.units_per_rev / self.steps_per_rev, 2)
