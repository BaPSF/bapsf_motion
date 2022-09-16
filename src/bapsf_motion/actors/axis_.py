__all__ = ["Axis"]

import astropy.units as u
import logging

from typing import Dict, Union

from bapsf_motion.actors.motor_ import Motor


class Axis:
    motor = None
    _logger = None
    _name = ""
    _units = None
    units_per_rev = None

    def __init__(
        self,
        *,
        ip: str,
        units: str,
        units_per_rev: float,
        name: str = None,
        logger=None,
        loop=None,
        auto_run=False
    ):
        self.setup_logger(logger, "Axis")
        self.motor = Motor(
            ip=ip,
            name=name,
            logger=self.logger,
            loop=loop,
            auto_start=False,
        )

        self._units = u.Unit(units)
        self.units_per_rev = units_per_rev

        if auto_run:
            self.run()

    def run(self):
        self.motor.run()

    def stop_running(self, delay_loop_stop=False):
        self.motor.stop_running(delay_loop_stop=delay_loop_stop)

    def setup_logger(self, logger, name):
        log_name = __name__ if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"
            self.name = name
        self._logger = logging.getLogger(log_name)

    @property
    def logger(self):
        return self._logger

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def units(self) -> u.Unit:
        return self._units

    @units.setter
    def units(self, new_units: u.Unit):
        if self.units.physical_type != new_units.physical_type:
            raise ValueError

        conversion = self.units.to(new_units)
        self.units_per_rev = conversion * self.units_per_rev

        self._units = new_units

    @property
    def steps_per_rev(self):
        return self.motor.steps_per_rev

    @property
    def position(self):
        pos = self.motor.position
        return self.convert_steps_to_units(pos)

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

    def convert_unit_to_steps(self, value):
        return value * self.steps_per_rev / self.units_per_rev

    def convert_steps_to_units(self, value):
        return round(value * self.units_per_rev / self.steps_per_rev, 2)
