__all__ = ["BaseActor"]

import logging


class BaseActor:
    def __init__(self, *, name: str = None, logger=None):
        # setup logger to track events
        log_name = "Actor" if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"

        self.name = name if name is not None else ""
        self.logger = logging.getLogger(log_name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value
