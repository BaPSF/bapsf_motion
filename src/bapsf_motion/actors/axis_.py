__all__ = ["Axis"]

from bapsf_motion.actors.base import BaseActor
from bapsf_motion.actors.motor_ import Motor
from bapsf_motion.utils import units as u


class Axis(BaseActor):
    """
    Examples
    --------

    >>> from bapsf_motion.actors import Axis
    >>> import logging
    >>> import sys
    >>> logging.basicConfig(stream=sys.stdout, level=logging.NOTSET)
    >>> ax = Axis(
    ...     ip="192.168.6.104",
    ...     units="cm",
    ...     units_per_rev=0.1*2.54,
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
        logger=None,
        loop=None,
        auto_run=False,
    ):
        super().__init__(logger=logger, name=name)

        self._init_instance_attrs()
        self.motor = Motor(
            ip=ip,
            name="motor",
            logger=self.logger,
            loop=loop,
            auto_start=False,
        )

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
        """Start the `asyncio` event loop."""
        self.motor.run()

    def stop_running(self, delay_loop_stop=False):
        """Stop the `asyncio` event loop."""
        self.motor.stop_running(delay_loop_stop=delay_loop_stop)

    @property
    def config(self):
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
        return [
            (u.steps, self.units),
            (u.steps / u.s, self.units / u.s),
            (u.steps / u.s / u.s, self.units / u.s / u.s),
            (u.rev / u.s, self.units / u.s),
            (u.rev / u.s / u.s, self.units / u.s / u.s),
        ]

    def send_command(self, command, *args):
        cmd_entry = self.motor._commands[command]
        motor_unit = cmd_entry["units"]  # type: u.Unit

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
        return self.send_command("move_to", *args)

    def stop(self):
        # not sending STOP command through send_command() since using
        # motor.stop() should result in faster execution
        return self.motor.stop()
