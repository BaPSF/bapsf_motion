__all__ = [
    "counts",
    "steps",
    "rev",
    "ipv4_pattern",
    "units",
    "SimpleSignal",
    "toml",
]
import re

from astropy import units

from bapsf_motion.utils import toml


#: Regular expression pattern for parsing IPv4 addresses
ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

#: Base unit for encoders.
counts = units.def_unit("counts", namespace=units.__dict__)

#: Base unit for stepper motors.
steps = units.def_unit("steps", namespace=units.__dict__)

#: An unit for the instance of revolving.
rev = units.def_unit("rev", namespace=units.__dict__)

for _u in {counts, steps, rev}:
    units.add_enabled_units(_u)


class SimpleSignal:
    _handlers = None

    @property
    def handlers(self):
        if self._handlers is None:
            self._handlers = []
        return self._handlers

    def connect(self, func):
        if func not in self.handlers:
            self.handlers.append(func)

    def disconnect(self, func):
        try:
            self.handlers.remove(func)
        except ValueError:
            pass

    def emit(self, payload):
        for handler in self.handlers:
            handler(payload)
