"""
Module of helper functions for the Configuration GUI.
"""
__all__ = ["gui_logger", "gui_logger_config_dict"]

import logging

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
