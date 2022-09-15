__all__ = ["Axis"]

import astropy.units as u
import logging

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

    def stop_running(self):
        self.motor.stop_running()

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

    def send_command(self, command, *args):
        self.motor.send_command(command, *args)
