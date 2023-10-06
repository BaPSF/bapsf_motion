"""
Module for functionality focused around the [Abstract] base actors.
"""

__all__ = ["BaseActor", "EventActor"]
__actors__ = ["BaseActor", "EventActor"]

import asyncio
import logging
import threading

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


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


class EventActor(BaseActor, ABC):
    def __init__(
        self,
        *,
        name: str = None,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
    ):

        super().__init__(name=name, logger=logger)

        self._thread = None
        self._loop = self.setup_event_loop(loop)
        self._tasks = None

        self._configure_before_run()
        self._initialize_tasks()

        self.run(auto_run)

    @property
    def tasks(self) -> List[asyncio.Task]:
        r"""
        List of `asyncio.Task`\ s this actor has in its `event loop`_.
        """
        if self._tasks is None:
            self._tasks = []

        return self._tasks

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """The `asyncio` :term:`event loop` for the actor."""
        return self._loop

    @property
    def thread(self) -> threading.Thread:
        """The `~threading.Thread` the `event loop`_ is running in."""
        return self._thread

    @property
    def _thread_id(self) -> Union[int, None]:
        """Unique ID for the thread the loop is running in."""
        if self.loop is None or not self.loop.is_running():
            # no loop has been created or loop is not running
            return None

        # get ident from running loop

        # return self.loop._thread_id if self._thread is None else self.thread.ident

        future = asyncio.run_coroutine_threadsafe(
            self._thread_id_async(),
            self.loop
        )
        return future.result(5)

    async def _thread_id_async(self):
        return threading.current_thread().ident

    @abstractmethod
    def _configure_before_run(self):
        ...

    @abstractmethod
    def _initialize_tasks(self):
        ...

    def setup_event_loop(self, loop: Optional[asyncio.AbstractEventLoop]):
        """
        Set up the `asyncio` `event loop`_.  If the given loop is not an
        instance of `~asyncio.AbstractEventLoop`, then a new loop will
        be created.

        Parameters
        ----------
        loop: `asyncio.AbstractEventLoop`
            `asyncio` `event loop`_ for the actor's tasks

        """
        # 1. loop is given and running
        #    - store loop
        # 2. loop is given and not running
        #    - store loop
        # 3. loop is NOT given
        #    - create new loop
        #    - store loop
        # get a valid event loop
        if loop is None:
            loop = asyncio.new_event_loop()
        elif not isinstance(loop, asyncio.AbstractEventLoop):
            self.logger.warning(
                "Given asyncio event is not valid.  Creating a new event loop to use."
            )
            loop = asyncio.new_event_loop()
        return loop

    def run(self, auto_run=True):
        """
        Activate the `asyncio` `event loop`_.   If the event loop is
        running, then nothing happens.  Otherwise, the event loop is
        placed in a separate thread and set to
        `~asyncio.loop.run_forever`.
        """
        if self.loop is None or self.loop.is_running() or not auto_run:
            return

        self._thread = threading.Thread(target=self._loop.run_forever)
        self._thread.start()

    def terminate(self, delay_loop_stop=False):
        r"""
        Stop the actor's `event loop`_\ .  All actor tasks will be
        cancelled, the connection to the motor will be shutdown, and
        the event loop will be stopped.

        Parameters
        ----------
        delay_loop_stop: bool
            If `True`, then do NOT stop the `event loop`_\ .  In this
            case it is assumed the calling functionality is managing
            additional tasks in the event loop, and it is up to that
            functionality to stop the loop.  (DEFAULT: `False`)

        """
        for task in list(self.tasks):
            task.cancel()
            self.tasks.remove(task)

        if delay_loop_stop:
            return

        self.loop.call_soon_threadsafe(self.loop.stop)
