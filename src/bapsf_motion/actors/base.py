"""
Module for functionality focused around the [Abstract] base actors.
"""

__all__ = ["BaseActor"]
__actors__ = ["BaseActor"]

import logging

from abc import ABC, abstractmethod
from typing import Any, Dict


# TODO: create an EventActor for an actor that utilizes asyncio event loops
#       - EventActor should inherit from BaseActor and ABC


class BaseActor(ABC):
    """
    Base class for any Actor class.

    Parameters
    ----------
    name : str, optional
        A unique :attr:`name` for the Actor instance.
    logger : `~logging.Logger`, optional
        The instance of `~logging.Logger` that the Actor should record
        events and status updates.

    Examples
    --------

    >>> ba = BaseActor(name="BoIt")
    >>> ba.name
    'DoIt'
    >>> ba.logger
    <Logger Actor.DoIt (WARNING)>
    >>> ba.logger.warning("This is a warning")
    This is a warning

    """

    def __init__(
        self, *, name: str = None, logger: logging.Logger = None,
    ):
        # setup logger to track events
        log_name = "Actor" if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"

        self.name = name if name is not None else ""
        self.logger = logging.getLogger(log_name)

    @property
    def name(self) -> str:
        """
        (`str`) A unique name given for the instance of the actor.  This
        name is used as an identifier in the actor logger (see
        :attr:`logger`).

        If the user does not specify a name, then the Actor should
        auto-generate a name.
        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def logger(self) -> logging.Logger:
        """The `~logger.Logger` instance being used for the actor."""
        return self._logger

    @logger.setter
    def logger(self, value):
        self._logger = value

    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """
        Configuration dictionary of the actor.

        .. warning::

           This dictionary should never be written to from outside the
           owning actor.
        """
        ...


# TODO: Create an EventActor
#       - must setup the asyncio event loop
#       - must handle running th loop in a separate thread
#       - How should I incorporate the heartbeat?
#       - Must have the option to auto_run the event loop
#       - must inherit from BaseActor
#       - will likely need abstract methods _actor_setup_pre_loop() and
#         _actor_setup_post_loop() for setup actions before and after
#         the loop creation, respectively.
