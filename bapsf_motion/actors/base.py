"""
Module for functionality focused around the [Abstract] base actors.
"""

__all__ = ["BaseActor", "EventActor"]
__actors__ = ["BaseActor", "EventActor"]

import asyncio
import concurrent.futures
import logging
import threading
import time

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from bapsf_motion.utils import loop_safe_stop


# TODO: create an EventActor for an actor that utilizes asyncio event loops
#       - EventActor should inherit from BaseActor and ABC


class BaseActor(ABC):
    """
    Low-level base class for any Actor class.

    Parameters
    ----------
    name : str, optional
        A unique :attr:`name` for the Actor instance.
    logger : `~logging.Logger`, optional
        The instance of `~logging.Logger` that the Actor should record
        events and status updates.
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
    r"""
    A base class for any Actor that will be interacting with an `asncio`
    event loop.

    Parameters
    ----------
    name : str, optional
        A unique :attr:`name` for the Actor instance.

    logger : `~logging.Logger`, optional
        The instance of `~logging.Logger` that the Actor should record
        events and status updates.

    loop: `asyncio.AbstractEventLoop`, optional
        Instance of an `asyncio` `event loop`_\ .  If `None`, then an
        `event loop`_ will be auto-generated.  (DEFAULT: `None`)

    auto_run: bool, optional
        If `True`, then the `event loop`_ will be placed in a separate
        thread and started.  This is all done via the :meth:`run`
        method. (DEFAULT: `False`)
    """

    def __init__(
        self,
        *,
        name: str = None,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
        parent: Optional["EventActor"] = None,
    ):

        if parent is not None and not isinstance(parent, EventActor):
            parent = None
        self._parent = parent

        super().__init__(name=name, logger=logger)

        self._terminated = False

        self._thread = None
        self._loop = self.setup_event_loop(loop)
        self._tasks = None

        self._configure_before_run()
        self._initialize_tasks()

        self.run(auto_run)

    @property
    def parent(self) -> Optional["EventActor"]:
        return self._parent

    @property
    def terminated(self):
        """Indicates if the actor has been terminated."""
        return self._terminated

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
        """
        The `~threading.Thread` the `event loop`_ is running in.

        If :attr:`loop` was given during instantiation, then there is
        no way of obtaining the thread object the event loop is
        running in.  In this case :attr:`thread` will be `None`.

        The thread id can always be retrieved using :attr:`_thread_id`.
        """
        return self._thread

    @property
    def _thread_id(self) -> Union[int, None]:
        """
        Unique ID for the thread the loop is running in.

        `None` if the :attr:`loop` does not exit or is not running.
        """
        if isinstance(self._thread, threading.Thread):
            return self._thread.ident

        if self.loop is None or not self.loop.is_running():
            # no loop has been created or loop is not running
            return None

        if (
            hasattr(self.parent, "thread")
            and isinstance(self.parent.thread, threading.Thread)
        ):
            return self.parent.thread.ident

        # we do not know if self._thread_id call came from insided the
        # event loop or outside...attempt getting the thread id via an
        # asyncio future...this will time out if self._thread_id was
        # called from inside the event loop
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._thread_id_async(),
                self.loop
            )
            thread_id = future.result(1)
            return thread_id
        except (concurrent.futures.TimeoutError, TimeoutError):
            pass

        # the future (^) timed-out...this likely happened since the
        # _thread_id() call came from inside another coroutine...lets
        # just get the id directly
        return threading.current_thread().ident

    @staticmethod
    async def _get_loop_thread():
        """
        Asyncio coroutine for retrieving the `threading.Thread` object
        the event loop is running in.
        """
        return threading.current_thread()

    @staticmethod
    async def _thread_id_async():
        """
        Asyncio coroutine for retrieving the id of the thread the event
        loop is running in.
        """
        return threading.current_thread().ident

    @abstractmethod
    def _configure_before_run(self):
        # A set of functionality for the subclass to run before the
        # asyncio tasks are created and the event loop is started.
        #
        # This method is executed by __init__ before the event loop is
        # started.
        ...

    @abstractmethod
    def _initialize_tasks(self):
        # Used by the subclass to initialize a list of tasks to be
        # executed in the event loop after the loop is started.
        #
        # This method is executed by __init__ after
        # _configure_before_run() but before the event loop is started.
        ...

    def setup_event_loop(
        self, loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """
        Set up the `asyncio` `event loop`_.  If the given loop is not an
        instance of `~asyncio.AbstractEventLoop`, then a new loop will
        be created.

        Parameters
        ----------
        loop: `asyncio.AbstractEventLoop`
            `asyncio` `event loop`_ for the actor's tasks

        """
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
        r"""
        Activate the `asyncio` `event loop`_\ .   If the event loop is
        running, then nothing happens.  Otherwise, the event loop is
        placed in a separate thread and set to
        `~asyncio.loop.run_forever`.

        Parameters
        ----------
        auto_run: `bool`, optional
            If `False`, then do NOT start the event loop.  This keyword
            is only made available to help with subclassing.
            (DEFAULT: `True`)
        """
        self._terminated = False
        if self.loop is None:
            return None

        if self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._get_loop_thread(),
                self.loop,
            )
            self._thread = future.result(5)
            return None

        if not auto_run:
            return None

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
            self.loop.call_soon_threadsafe(task.cancel)
            try:
                self.tasks.remove(task)
            except ValueError:
                # a remove callback was set up on this task
                pass

        tstart = datetime.now()
        while len(self.tasks) != 0:
            for task in list(self.tasks):
                if task.done() or task.cancelled():
                    try:
                        self.tasks.remove(task)
                    except ValueError:
                        pass

            if (datetime.now() - tstart).total_seconds() > 6.0:
                break
            else:
                time.sleep(0.1)

        self._terminated = True

        if delay_loop_stop:
            return

        loop_safe_stop(self.loop)
