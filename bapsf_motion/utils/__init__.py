"""Utility functionality for `bapsf_motion`."""
__all__ = [
    "counts",
    "steps",
    "rev",
    "ipv4_pattern",
    "load_example",
    "units",
    "SimpleSignal",
    "toml",
    "loop_safe_stop",
    "dict_equal"
]
import asyncio
import re
import time

from astropy import units
from collections import UserDict
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Union

from bapsf_motion.utils import exceptions, toml
from bapsf_motion.utils.units_ import units, counts, steps, rev

_HERE = Path(__file__).resolve().parent
_EXAMPLES = (_HERE / ".." / "examples").resolve()

#: Regular expression pattern for parsing IPv4 addresses
ipv4_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


class SimpleSignal:
    """
    A very simple, rudimentary class for creating signals.
    """
    _handlers = None

    @property
    def handlers(self) -> Union[None, List[Callable]]:
        """List of callbacks/handlers connect to the signal."""
        if self._handlers is None:
            self._handlers = []
        return self._handlers

    def connect(self, func: Callable):
        """
        Connect the callback/handler ``func`` to the signal.  The
        callback should take no arguments.
        """
        if not callable(func):
            return None

        if func not in self.handlers:
            self.handlers.append(func)

    def disconnect(self, func=None):
        """
        Disconnect the callback/handler ``func`` from the signal.
        """
        try:
            self.handlers.remove(func)
        except ValueError:
            pass

    def disconnect_all(self):
        """
        Disconnect all callbacks/handlers for the signal.
        """
        self._handlers = None

    def emit(self):
        """Emit the signal, which executes all the connected handlers."""
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


def dict_equal(d1, d2) -> bool:
    if not isinstance(d1, (dict, UserDict)) or not isinstance(d2, (dict, UserDict)):
        return False

    if set(d1) != set(d2):
        return False

    for key, val in d1.items():
        if isinstance(val, (dict, UserDict)):
            equality = dict_equal(val, d2[key])

            if not equality:
                return False

        if val != d2[key]:
            return False

    return True


def loop_safe_stop(loop: asyncio.AbstractEventLoop, max_wait: Optional[float] = 6.0):
    """
    Safely cancel all tasks in the `event loop`_ ``loop`` and stop the
    loop once the tasks are done.

    Parameters
    ----------
    loop : `asyncio.AbstractEventLoop`
        The `asyncio` `event loop`_ to be stopped.

    max_wait : `float`, optional
        Max wait time in seconds for tasks to finish before stopping
        the event loop.

    """
    if loop.is_closed() or not loop.is_running():
        return

    if not isinstance(max_wait, (int, float)):
        max_wait = 6.0

    # if we're stopping the loop, then all tasks need to be cancelled
    for task in asyncio.all_tasks(loop):
        if not task.done() or not task.cancelled():
            loop.call_soon_threadsafe(task.cancel)

    tstart = datetime.now()
    while any(
            not (task.done() or task.cancelled())
            for task in asyncio.all_tasks(loop)
    ):
        # continue waiting for all tasks to be cancelled
        if (datetime.now() - tstart).total_seconds() > max_wait:
            break
        else:
            time.sleep(0.1)

    loop.call_soon_threadsafe(loop.stop)
