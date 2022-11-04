__all__ = ["BaseActor"]

import logging

# TODO: create an EventActor for an actor that utilizes asyncio event loops
#       - EventActor should inherit from BaseActor and ABC


class BaseActor:
    def __init__(self, *, name: str = None, logger=None):
        # setup logger to track events
        log_name = "Actor" if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"

        self.name = name if name is not None else ""
        self.logger = logging.getLogger(log_name)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value


# TODO: Create an EventActor
#       - must setup the asyncio event loop
#       - must handle running th loop in a separate thread
#       - How should I incorporate the heartbeat?
#       - Must have the option to auto_run the event loop
#       - must inherit from BaseActor
#       - will likely need abstract methods _actor_setup_pre_loop() and
#         _actor_setup_post_loop() for setup actions befroe and after
#         the loop creation, respectively.
