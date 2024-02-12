__all__ = [
    "counts",
    "steps",
    "rev",
    "ipv4_pattern",
    "load_example",
    "units",
    "SimpleSignal",
    "toml",
]
import re

from astropy import units
from collections import UserDict
from pathlib import Path

from bapsf_motion.utils import exceptions, toml

_HERE = Path(__file__).resolve().parent
_EXAMPLES = (_HERE / ".." / "examples").resolve()

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

    def disconnect(self, func=None):
        if func is None:
            self._handlers = None
            return

        try:
            self.handlers.remove(func)
        except ValueError:
            pass

    def emit(self):
        for handler in self.handlers:
            handler()


def load_example(filename: str, as_string=False):
    """
    Load an example TOML file from `bapsf_motion.examples`.

    Parameters
    ----------
    filename: `str`
        Name of the example file, including extension.

    as_string: `bool`, optional
        If `True`, then return the example configuration as a TOML
        string; otherwise, return the configuration as a dictionary.
        (DEFAULT:`False`)

    Returns
    -------
    config: `dict` or `str`
        Return the example configuration.
    """
    _file = (_EXAMPLES / filename).resolve()

    if not _file.exists():
        raise ValueError(
            f"The specified example file {filename} does not exist in "
            f"the examples directory {_EXAMPLES}."
        )
    elif not _file.is_file():
        raise ValueError(f"The specified example file {filename} is not a file.")

    with open(_file, "rb") as f:
        config = toml.load(f)

    if as_string:
        config = toml.dumps(config)

    return config


def _deepcopy_dict(item):
    _copy = {}
    for key, val in item.items():
        if isinstance(val, (dict, UserDict)):
            val = _deepcopy_dict(val)

        _copy[key] = val

    return _copy
