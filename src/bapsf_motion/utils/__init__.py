__all__ = ["ipv4_pattern", "units", "SimpleSignal"]
import re

from astropy import units

ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")

counts = units.def_unit("counts", namespace=units.__dict__)
steps = units.def_unit("steps", namespace=units.__dict__)
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
