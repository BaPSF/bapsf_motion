"""
Module of helper functions for the Configuration GUI.
"""
__all__ = ["gui_logger", "gui_logger_config_dict", "read_parameter_hints"]

import logging

from pathlib import Path

from bapsf_motion.utils import toml

_HERE = Path(__file__)

gui_logger = logging.getLogger("GUI")

gui_logger_config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "class": "logging.Formatter",
            "format": "%(asctime)s - [%(levelname)s] { %(name)s }  %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {  # root logger
            "level": "WARNING",
            "handlers": ["stderr", "stdout"],
            "propagate": True,
        },
        "GUI": {
            "level": "DEBUG",
            "handlers": [],
            "propagate": True,
        },
        "RM": {
            "level": "DEBUG",
            "handlers": [],
            "propagate": True,
        },
    },
}
"""
Configuration dictionary to setup/configure the logging environment
association with the `bapsf_motion.gui.configure` functionality.

This dictionary is intended to be passed directly to 
`logging.config.dictConfig`.
"""


def read_parameter_hints() -> dict:
    """
    Read the parameter hints file :file:`parameter_hints.toml` and
    return the dictionary of hints.
    """
    filepath = (_HERE.parent / "parameter_hints.toml").resolve()
    with open(filepath, "rb") as f:
        hints = toml.load(f)

    if "hints" not in hints:
        return dict()

    return hints["hints"]
