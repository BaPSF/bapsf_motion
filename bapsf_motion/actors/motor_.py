"""
Module for functionality focused around the
`~bapsf_motion.actors.motor_.Motor` actor class.
"""
__all__ = ["do_nothing", "CommandEntry", "Motor", "MotorSignals"]
__actors__ = ["Motor"]

import asyncio
import errno
import logging
import numpy as np
import re
import socket
import threading
import time

from collections import UserDict
from enum import Enum
from typing import Any, AnyStr, Callable, Dict, NamedTuple, Optional, Union

from bapsf_motion.actors.base import EventActor
from bapsf_motion.utils import ipv4_pattern, SimpleSignal, dict_equal
from bapsf_motion.utils import units as u


def do_nothing(x):
    """Return argument ``x`` unchanged."""
    return x


class AckFlags(Enum):
    ACK = 1
    ACK_QUEUED = 2
    NACK = 3
    LOST_CONNECTION = 4
    MALFORMED = 5


class _HeartRate(NamedTuple):
    BASE = 1.5  # seconds
    ACTIVE = 0.2
    SEARCHING = 3.0
    PAUSE = 5.0


class CommandEntry(UserDict):
    r"""
    A `dict` containing all the necessary information to define a
    command that is sent to an ethernet based stepper motor.

    Parameters
    ----------

    command: str
        Name of the command.  If the command entry is also a method
        command, then this must be the name of the class method to
        be called.

    send: str
        The base `str` command that is sent to the motor.

    send_processor: :term:`callable`, optional
        A callable object that processes the command argument before
        the full command is sent to the motor.  The callable must
        return a string that is concatenated with the ``send`` command
        to form the full command.  If `None`, then the command is
        assumed to have no argument. (DEFAULT: `None`)

    recv: re.Pattern, optional
        A `re` compiled pattern to expression match any received string
        from the sent command.  If `None`, then no expression matching
        is performed on the returned string.  If a pattern is defined,
        then the pattern must define a return group
        (i.e. ``'(?P<return>...)'``).  This return group is assumed to
        be the returned argument and will be further processed by the
        ``recv_processor``. (DEFAULT: `None`)

    recv_processor: :term:`callable`, optional
        A callable object that will process the returned argument from
        the sent command.  The returned command is always in the form
        of a string, so the processor must take a string and process
        that it into any desirable type.  If `None`, then no processing
        is performed. (DEFAULT:
        `~bapsf_motion.actors.motor_.do_nothing`)

    two_way: bool, optional
        The command both sends and receives arguments from the motor.
        (DEFAULT: `False`)

    units: :term:`unit-like`, optional
        An object that represents the units of the sent and/or returned
        arguments.  These units will converted into `astropy.units` and
        will become the default units for any argument sent or received
        by this defined command.  (DEFAULT: `None`)

    method_command: bool
        If `True`, then the defined command is a method command.  A
        method command is an advanced motor command (e.g. ``move_to``)
        that requires multiple base commands to be performed in a
        particular sequence.  Thus, the ``command`` argument defines
        the name of a class method that will be executed for this
        command. (DEFAULT: `False`)

    Examples
    --------
    An example of a typical motor command entry...

    .. code-block:: python

        ce = CommandEntry(
            "speed",
            send="VE",
            send_processor=lambda value: f"{float(value):.4f}",
            recv=re.compile(r"VE=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s,
        )

    An example of a method based motor command entry.  A method based
    command is reserved for more advanced commands that typically
    require multiple base commands to be sent in a particular sequence.

    .. code-block:: python

        ce = CommandEntry(
            "move_to",
            send="",
            units=u.steps,
            method_command=True,
        )
    """

    # TODO: elaborate on examples in the docstring to describe exactly
    #       how the defined command would work

    def __init__(
        self,
        command: str,
        *,
        send: str,
        send_processor: Optional[Callable[[Any], str]] = None,
        recv: Optional["re.Pattern"] = None,
        recv_processor: Optional[Callable[[str], Any]] = do_nothing,
        two_way: bool = False,
        units: Union[str, u.Unit, None] = None,
        method_command: Optional[bool] = False,
    ):
        self._command = command

        _dict = {
            "two_way": False,
            "method_command": method_command,
        }
        if not method_command:
            _dict = {
                "send": send,
                "send_processor": send_processor,
                "recv": recv,
                "recv_processor": recv_processor,
                "two_way": two_way,
                "units": units,
                "method_command": method_command,
            }
        else:
            _dict = {
                "two_way": False,
                "units": units,
                "method_command": method_command,
            }
        super().__init__(**_dict)

    @property
    def command(self) -> str:
        """
        Name of the command.  If the command entry is also a method
        command, then this is the name of the class method to be called.
        """
        return self._command


class MotorSignals:
    r"""
    Class that defines all the `~bapsf_motion.utils.SimpleSignal`\ 's
    used by `Motor`.
    """
    def __init__(self):
        self._status_changed = SimpleSignal()
        self._movement_started = SimpleSignal()
        self._movement_finished = SimpleSignal()

    @property
    def status_changed(self) -> SimpleSignal:
        """
        `~bapsf_motion.utils.SimpleSignal` emitted when the motor
        `~Motor.status` is changes."""
        return self._status_changed

    @property
    def movement_started(self) -> SimpleSignal:
        """
        `~bapsf_motion.utils.SimpleSignal` emitted when the motor
        movement is started.
        """
        return self._movement_started

    @property
    def movement_finished(self) -> SimpleSignal:
        """
        `~bapsf_motion.utils.SimpleSignal` emitted when the motor
        movement is completed.
        """
        return self._movement_finished


class Motor(EventActor):
    """
    An actor class for directly communicating to an ethernet based
    stepper motor.  This actor is only aware of the motor, and is
    ignorant of how it is situated within a probe drive.  Thus, all
    units are in motor units, i.e. steps, counts, rev, and sec.

    Parameters
    ----------
    ip: `str`
        IPv4 address for the motor

    limit_mode : `int`, optional
        Define the operational mode of the motor limit switches. Value
        should be an integer of value 1, 2, or 3.  1 indicates limit
        is activated when energized, 2 indicates limit is activated
        when de-energized, and 3 indicates no limits. (DEFAULT: ``1``)

    current : `float`, optional
        A value between 0 (non-inclusive) and 1 (inclusive) which
        indicates what the motor current should be set to as a fraction
        of the max allowed current ``motor["DEFAULTS"]["max_current"]``.
        (DEFUALT: ``0.8``)

    name: `str`, optional
        Name the motor.  If `None`, then the name will be automatically
        generated. (DEFAULT: `None`)

    logger: `~logging.Logger`, optional
        An instance of `~logging.Logger` that the Actor will record
        events and status updates to.  If `None`, then a logger will
        automatically be generated. (DEFUALT: `None`)

    loop: `asyncio.AbstractEventLoop`, optional
        Instance of an `asyncio` `event loop`_. Communication with the
        motor will happen primaritly through the evenet loop.  If
        `None`, then an `event loop`_ will be auto-generated.
        (DEFAULT: `None`)

    auto_run: bool, optional
        If `True`, then the `event loop`_ will be placed in a separate
        thread and started.  This is all done via the :meth:`run`
        method. (DEFAULT: `False`)

    Examples
    --------

    Using `Motor` with ``auto_start=True``.

    >>> import logging
    >>> logging.basicConfig(level=logging.NOTSET)
    >>> lgr = logging.getLogger()
    >>> m1 = Motor(
    ...     ip="192.168.0.70",
    ...     name="m1",
    ...     logger=lgr,
    ...     auto_run=True,
    ... )
    >>> # now stop the actor, which stops the event loop
    >>> m1.terminate()

    Using `Motor` with ``auto_start=False``.

    >>> import logging
    >>> logging.basicConfig(level=logging.NOTSET)
    >>> lgr = logging.getLogger()
    >>> m1 = Motor(
    ...     ip="192.168.0.70",
    ...     name="m1",
    ...     logger=lgr,
    ... )
    >>> # start the actor, with starts the event loop
    >>> m1.run()
    >>> # now stop the actor, which stops the event loop
    >>> m1.terminate()
    """
    #: available commands that can be sent to the motor
    _commands = {
        "acceleration": CommandEntry(
            "acceleration",
            send="AC",
            send_processor=lambda value: f"{float(value):.3f}",
            recv=re.compile(r"AC=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s / u.s,
        ),
        "alarm": CommandEntry(
            "alarm",
            send="AL",
            recv=re.compile(r"AL=(?P<return>[0-9]{4})"),
        ),
        "alarm_reset": CommandEntry(
            "alarm_reset",
            send="AR"
        ),
        "buffer_size": CommandEntry(
            "buffer_size",
            send="BS",
            recv=re.compile(r"BS=(?P<return>[0-9]\.?[0-9]?)"),
            recv_processor=int,
        ),
        "commence_jogging": CommandEntry("commence_jogging", send="CJ"),
        "continuous_jog": CommandEntry(
            "continuous_jog",
            send="",
            method_command=True,
        ),
        "current": CommandEntry(
            "change_current",
            send="CC",
            send_processor=lambda value: f"{float(value):.1f}",
            recv=re.compile(r"CC=(?P<return>[0-9]\.?[0-9]?)"),
            recv_processor=float,
            two_way=True,
        ),
        "deceleration": CommandEntry(
            "deceleration",
            send="DE",
            send_processor=lambda value: f"{float(value):.3f}",
            recv=re.compile(r"DE=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s / u.s,
        ),
        "define_limits": CommandEntry(
            "define_limits",
            send="DL",
            send_processor=lambda value: f"{int(value)}",
            recv=re.compile(r"DL=(?P<return>[0-9])"),
            recv_processor=int,
            two_way=True,
        ),
        "disable": CommandEntry("disable", send="MD"),
        "enable": CommandEntry("enable", send="ME"),
        "encoder_position":  CommandEntry(
            "encoder_position",
            send="EP",
            send_processor=lambda value: f"{int(value)}",
            recv=re.compile(r"EP=(?P<return>[0-9]+)"),
            recv_processor=int,
            two_way=True,
            units=u.counts,
        ),
        "encoder_resolution": CommandEntry(
            "encoder_resolution",
            send="ER",
            recv=re.compile(r"ER=(?P<return>[0-9]+)"),
            recv_processor=int,
            units=u.counts / u.rev,
        ),
        "feed": CommandEntry("feed", send="FP"),
        "gearing": CommandEntry(
            "gearing",
            send="EG",
            recv=re.compile(r"EG=(?P<return>[0-9]+)"),
            recv_processor=int,
            units=u.steps / u.rev,
        ),
        "get_position": CommandEntry(
            "immediate_position",
            send="IP",
            recv=re.compile(r"IP=(?P<return>-?[0-9]+)"),
            recv_processor=int,
            units=u.steps,
        ),
        "idle_current": CommandEntry(
            "change_idle_current",
            send="CI",
            send_processor=lambda value: f"{float(value):.1f}",
            recv=re.compile(r"CI=(?P<return>[0-9]\.?[0-9]?)"),
            recv_processor=float,
            two_way=True,
        ),
        "jog_acceleration": CommandEntry(
            "jog_acceleration",
            send="JA",
            send_processor=lambda value: f"{float(value):.3f}",
            recv=re.compile(r"JA=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s / u.s,
        ),
        "jog_deceleration": CommandEntry(
            "jog_deceleration",
            send="JL",
            send_processor=lambda value: f"{float(value):.3f}",
            recv=re.compile(r"JL=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s / u.s,
        ),
        "jog_speed": CommandEntry(
            "jog_speed",
            send="JS",
            send_processor=lambda value: f"{float(value):.4f}",
            recv=re.compile(r"JS=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s,
        ),
        "kill": CommandEntry(
            "stop_and_kill",  # immediately stop moving and erase queue
            send="SK",
        ),
        "move_off_limit": CommandEntry(
            "move_off_limit",
            send="",
            method_command=True,
        ),
        "move_to": CommandEntry(
            "move_to",
            send="",
            units=u.steps,
            method_command=True,
        ),
        "protocol": CommandEntry(
            "protocol",
            send="PR",
            send_processor=lambda value: f"{int(value)}",
            recv=re.compile(r"PR=(?P<return>[0-9]{1,3})"),
            recv_processor=int,
            two_way=True,
        ),
        "request_status": CommandEntry(
            "request_status",
            send="RS",
            recv=re.compile(r"RS=(?P<return>[ADEFHJMPRSTW]+)"),
        ),
        "reset_currents": CommandEntry(
            "reset_currents",
            send="",
            method_command=True,
        ),
        "retrieve_motor_alarm": CommandEntry(
            "retrieve_motor_alarm",
            send="",
            method_command=True,
        ),
        "retrieve_motor_status": CommandEntry(
            "retrieve_motor_status",
            send="",
            method_command=True,
        ),
        "set_current": CommandEntry(
            "set_current",
            send="",
            method_command=True,
        ),
        "set_idle_current": CommandEntry(
            "set_idle_current",
            send="",
            method_command=True,
        ),
        "set_position": CommandEntry(
            "set_position",
            send="",
            method_command=True,
            units=u.steps,
        ),
        "set_position_SP": CommandEntry(
            "set_position_SP",
            send="SP",
            send_processor=lambda value: f"{int(value)}",
            recv=re.compile(r"SP=(?P<return>[0-9]+)"),
            recv_processor=int,
            two_way=True,
            units=u.steps,
        ),
        "speed": CommandEntry(
            "speed",
            send="VE",
            send_processor=lambda value: f"{float(value):.4f}",
            recv=re.compile(r"VE=(?P<return>[0-9]+\.?[0-9]*)"),
            recv_processor=float,
            two_way=True,
            units=u.rev / u.s,
        ),
        "stop": CommandEntry(
            "stop",
            send="SK",
            send_processor=lambda soft: "D" if bool(soft) else "",
        ),
        "target_distance": CommandEntry(
            "target_distance",
            send="DI",
            send_processor=lambda value: f"{int(value)}",
            recv=re.compile(r"DI=(?P<return>[0-9]+)"),
            recv_processor=int,
            two_way=True,
            units=u.steps,
        ),
        "zero": CommandEntry(
            "zero",
            send="",
            method_command=True,
            units=u.steps,
        ),
    }  # type: Dict[str, Optional[Dict[str, Any]]]

    #: mapping of motor alarm codes to their descriptive message (specific to STM motors)
    _alarm_codes = {
        1: "position limit [Drive Fault]",
        2: "CCW limit",
        4: "CW limit",
        8: "over temp  [Drive Fault]",
        10: "internal voltage [Drive Fault]",
        20: "over voltage [Drive Fault]",
        40: "under voltage",
        80: "over current [Drive Fault]",
        100: "open motor winding [Drive Fault]",
        400: "common error",
        800: "bad flash",
        1000: "no move",
        4000: "blank Q segment",
    }

    #: mapping of motor Ack/Nack codes and their descriptive messages
    _nack_codes = {
        1: "command timed out",
        2: "parameter is too long",
        3: "too few parameters",
        4: "too many parameters",
        5: "parameters out of range",
        6: "command buffer (queue) full",
        7: "cannot process command",
        8: "program running",
        9: "bad password",
        10: "comm port error",
        11: "bad character",
        12: "I/O point already used by curren command mode, and cannot "
            "be changed (Flex I/O drives only)",
        13: "I/O point configured for incorrect use "
            "(i.e., input vs. output) (Flex I/O drives only)",
        14: "I/O point cannot be used for requested function - see HW "
            "manual for possible I/O function assignments. "
            "(Flex I/O drives only)",
    }

    ack_flags = AckFlags

    # TODO: update _heartbeat so the beat happens on the specified HR
    #       interval instead of execution time + HR interval
    # TODO: implement a "jog_by" "FL" "feed to length"
    # TODO: implement commands for setting/getting jog speed, accel,
    #       and decel
    # TODO: implement a "soft_stop"
    # TODO: integrate hard limits
    # TODO: integrate soft limits
    # TODO: move off limit command
    # TODO: integrate homing
    # TODO: integrate zeroing
    # TODO: get motor firmware version, model numer, and sub-model using "MV"
    # TODO: upgrade commands so setting and getting commands run
    #       through the same general command (e.g. set_speed and
    #       get_speed are just aliases for the speed command)
    # TODO: Do I need to store feed target, spead, accel, and decel?
    #       Same for the jog equivalent.
    # TODO: reconcile the implementation of properties name and logger
    #       between the Motor class and the BaseActor class...BaseActor
    #       defines these as instance variable but Motor defines them
    #       in the self._setup...we shouldn't be redoing implementations
    # TODO: create a method that lists all available commands
    # TODO: create a method the shows a commands definition
    #       (i.e. self._commands[command])

    def __init__(
        self,
        *,
        ip: str,
        limit_mode: int = None,
        current: float = 0.8,
        name: str = None,
        logger: logging.Logger = None,
        loop: asyncio.AbstractEventLoop = None,
        auto_run: bool = False,
        parent: Optional["EventActor"] = None,
    ):

        self._heartbeat_task = []

        self._setup = self._setup_defaults.copy()
        self._motor = self._motor_defaults.copy()
        self._status = self._status_defaults.copy()
        self._limit_mode = limit_mode
        if isinstance(current, float) and 0.0 < current <= 1.0:
            self._motor["DEFAULTS"]["current"] = current

        # simple signal to tell handlers that _status changed
        self._signals = MotorSignals()

        self.ip = ip

        self._pause_heartbeat = False

        try:
            super().__init__(
                name=name,
                logger=logger,
                loop=loop,
                auto_run=False,
                parent=parent,
            )
        except ConnectionError as err:
            self.logger.warning("Unable to connect to motor.", exc_info=err)
            self.terminate(delay_loop_stop=True)

        if not self.terminated:
            self.run(auto_run=auto_run)

    def _configure_before_run(self):
        # actions to be done during object instantiation, but before
        # the asyncio event loop starts running.
        if self._limit_mode is None:
            self._limit_mode = self.motor["define_limits"]
        elif not isinstance(self._limit_mode, int):
            self.logger.warning(
                "Assuming limit mode 1 for input argument 'limit_mode'.",
                exc_info=TypeError(
                    "Was expecting an int of value 1, 2, or 3 for input "
                    f"argument 'limit_mode', got type "
                    f"{type(self._limit_mode)} instead."
                ),
            )
            self._limit_mode = self.motor["define_limits"]
        elif self._limit_mode not in (1, 2, 3):
            self.logger.warning(
                "Assuming limit mode 1 for input argument 'limit_mode'.",
                exc_info=ValueError(
                    "Was expecting an int of value 1, 2, or 3 for input "
                    f"argument 'limit_mode', got value "
                    f"{self._limit_mode} instead."
                ),
            )
            self._limit_mode = self.motor["define_limits"]
        else:
            self.motor["define_limits"] = self._limit_mode

        self.connect()

        # self.start_heartbeat()
        # self._pause_heartbeat = True

        self._configure_motor()
        self._get_motor_parameters()
        self.send_command("retrieve_motor_status")

        # self._pause_heartbeat = False

    def _initialize_tasks(self):
        # The heartbeat task was initialized in _configure_before_run
        # self.start_heartbeat()
        return

    def run(self, auto_run=True):

        # if actor was terminated, actor is restarting
        self._terminated = False

        if (
            self.heartbeat_task is None
            or self.heartbeat_task.done()
            or self.heartbeat_task.cancelled()
        ):
            self._configure_before_run()
            self._initialize_tasks()

        super().run(auto_run=auto_run)

    @property
    def connected(self):
        """
        `True` if the TCP connection is established with the physical
        motor.
        """
        return self.status["connected"]

    @property
    def _setup_defaults(self) -> Dict[str, Any]:
        """Default values for :attr:`setup`."""
        return {
            "name": "",
            "logger": None,
            "loop": None,
            "thread": None,
            "socket": None,
            "tasks": None,
            "max_connection_attempts": 1,
            "heartrate": _HeartRate(),  # in seconds
            "port": 7776,  # 7776 is Applied Motion's TCP port, 7775 is the UDP port
        }

    @property
    def setup(self):
        """
        Dictionary of class setup parameters.
        """
        _setup = {
            **self._setup,
            "name": self.name,
            "logger": self.logger,
            "loop": self.loop,
            "thread": self.thread,
            "tasks": self.tasks,
            "socket": self.socket,
        }
        self._setup = _setup
        return self._setup

    @property
    def _motor_defaults(self) -> Dict[str, Any]:
        """Default values for :attr:`motor`."""
        return {
            "ip": None,
            "manufacturer": "Applied Motion Products",
            "model": "STM23S-3EE",
            "gearing": None,  # steps/rev
            "encoder_resolution": None,  # counts/rev
            "DEFAULTS": {
                "speed": 12.5,
                "accel": 25,
                "decel": 25,
                "idle_current": 0.3,  # 30% of current
                "current": 0.8,  # 80% of max_current (4.0 amps)
                "max_idle_current": 0.9,  # 90% of current
                "max_current": 5.0  # 5 amps
            },
            "speed": None,
            "accel": None,
            "decel": None,
            "protocol_settings": None,
            "define_limits": 1,  # 1 = energized, 2 = de-energized, 3 = None
        }

    @property
    def motor(self) -> Dict[str, Any]:
        """
        Dictionary containing properties of the Applied Motion STM
        motor.
        """
        return self._motor

    @property
    def signals(self) -> MotorSignals:
        """
        Collection of all the signals emitted by the `Motor` class.

        See `MotorSignals` for additional documentation on the
        individual signals.
        """
        return self._signals

    @property
    def _status_defaults(self) -> Dict[str, Any]:
        """Default values for :attr:`status`."""
        return {
            "connected": False,
            "position": None,
            "alarm": None,
            "enabled": None,
            "fault": None,
            "moving": None,
            "homing": None,
            "jogging": None,
            "motion_in_progress": None,
            "in_position": None,
            "stopping": None,
            "waiting": None,
            "limit": {
                "CW": False,
                "CCW": False,
            },
        }

    @property
    def status(self) -> Dict[str, Any]:
        """Current status of the motor."""
        # TODO: dictionary keys and explanations to the docstring
        return self._status

    def _lost_connection(self, rtn: Any = None):
        """
        Check if the motor connection was lost by examining the return
        value from send_command.
        """
        if rtn is None:
            return not self.connected
        elif isinstance(rtn, self.ack_flags) and rtn == self.ack_flags.LOST_CONNECTION:
            return True
        return False

    def _configure_motor(self):
        """
        Configure motor behavior for suitable operation with the actor.

        This configuration should be performed during object
        instantiation and upon re-connecting.
        """
        # ensure motor always sends Ack/Nack
        # - Needs to be set before any commands are sent, otherwise
        #   receiving will time out and throw an Exception on commands
        #   that do not return a reply
        self._read_and_set_protocol()

        # enable limit switches if present...end-of-travel limit occurs when an
        # input is closed (energized)
        # TODO: Replace with normal send_command when "define_limits" command
        #       is added to _commands dict
        self.send_command("define_limits", self.motor["define_limits"])

        # set format of immediate commands to decimal
        self._send_raw_command("IFD")

        # set a slower speed
        self.send_command("speed", 4.0)
        self.send_command("jog_speed", 4.0)

        # set currents
        self.send_command("set_current", self.motor["DEFAULTS"]["current"])
        self.send_command("set_idle_current", self.motor["DEFAULTS"]["idle_current"])

    def _read_and_set_protocol(self):
        """
        Read and set the motor protocol settings.  For proper
        behavior between the motor and actor, the motor should be set
        to always return an Ack/Nack acknowledgement for every sent
        command.

        The 'protocol' command returns an integer that can be converted
        into a 9-bit binary word.  Each bit in that word represent
        a unique protocol setting.

        bit 0 = Default ('Standard SCL')
        bit 1 = Always use Address Character
        bit 2 = Always return Ack/Nack
        bit 3 = Checksum
        bit 4 = (reserved)
        bit 5 = 3-digit numeric register addressing
        bit 6 = Checksum Type (step-servo and SV200 only)
        bit 7 = Little/Big Endian in Modbus Mode
        bit 8 =Full Duplex in RS-422
        """
        rtn = self.send_command("protocol")
        if self._lost_connection(rtn) or rtn == self.ack_flags.MALFORMED:
            return
        _bits = f"{rtn:09b}"

        if _bits[-3] == "0":
            # motor does not always respond with ack/nack, change
            # protocol, so it does
            _bits = list(_bits)
            _bits[-3] = "1"  # sets always ack/nack
            _bits = "".join(_bits)
            _bits = int(_bits, 2)

            self.send_command("protocol", _bits)

            # if Ack/Nack was not set to begin with, then the first protocol
            # setting will not have an Ack/Nack return.  Thus, lets retrieve
            # the protocol again.
            #
            rtn = self.send_command("protocol")
            if self._lost_connection(rtn) or rtn == self.ack_flags.MALFORMED:
                return
            _bits = f"{rtn:09b}"

        self._motor["protocol_settings"] = []
        _bit_descriptions = [
            "Default ('Standard SCL')",
            "Always use Address Character",
            "Always return Ack/Nack",
            "Checksum",
            "(reserved)",
            "3-digit numeric register addressing",
            "Checksum Type (step-servo and SV200 only)",
            "Little/Big Endian in Modbus Mode",
            "Full Duplex in RS-422",
        ]
        for ii, b in enumerate(list(_bits)):
            if b == "0":
                continue

            bit_num = 8 - ii
            self._motor["protocol_settings"].append(_bit_descriptions[bit_num])

    def _get_motor_parameters(self):
        """Get current motor parameters."""
        self._motor.update(
            {
                "gearing": self.send_command("gearing"),
                "encoder_resolution": self.send_command("encoder_resolution"),
                "speed": self.send_command("speed"),
                "accel": self.send_command("acceleration"),
                "decel": self.send_command("deceleration"),
            }
        )

    @property
    def ip(self) -> str:
        """IPv4 address for the motor"""
        return self._motor["ip"]

    @ip.setter
    def ip(self, value):
        # TODO: update ipv4_pattern so the port number can be passed with the
        #       ip argument
        if self._motor["ip"] is not None:
            self.logger.warning(
                "The motor's IP address can only be defined at object "
                "instantiation."
            )
            return

        if ipv4_pattern.fullmatch(value) is None:
            raise ValueError(f"Supplied IP address ({value}) is not a valid IPv4.")

        self._motor["ip"] = value

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ip": self.ip,
            "limit_mode": self.motor["define_limits"],
            "current": self.motor["DEFAULTS"]["current"],
        }
    config.__doc__ = EventActor.config.__doc__

    @property
    def heartrate(self) -> _HeartRate:
        """
        Heartrate of the motor monitor, or the time (in sec) between
        motor checks.  There are two different heartrates:
        (1) ``heartrate.base`` for when the motor is not moving, and
        (2) ``heartrate.active`` for when the motor is moving.
        """
        return self._setup["heartrate"]

    @property
    def steps_per_rev(self) -> u.steps/u.rev:
        """The number of steps the motor does per revolution."""
        return self._motor["gearing"]

    @property
    def port(self) -> int:
        """Port used for motor communication."""
        return self._setup["port"]

    @property
    def socket(self) -> socket.socket:
        """Instance of the socket used for motor communication."""
        return self._setup["socket"]

    @socket.setter
    def socket(self, value):
        if not isinstance(value, socket.socket):
            raise TypeError(f"Expected type {socket.socket}, got type {type(value)}.")

        self._setup["socket"] = value

    @property
    def is_moving(self) -> bool:
        """`True` if the motor is actively moving, `False` otherwise."""
        is_moving = self.status["moving"]
        if is_moving is None:
            return False
        return is_moving

    @property
    def position(self) -> u.steps:
        """
        Current position of the motor, in motor units
        `~bapsf_motion.utils.steps`.
        """
        if (
            self.loop.is_running()
            and self.heartbeat_task is not None
            and not self.heartbeat_task.done()
            and not self.heartbeat_task.cancelled()
        ):
            # read from status if the heartbeat is operational
            return self.status["position"]

        pos = self.send_command("get_position")
        if not isinstance(pos, self.ack_flags):
            self._update_status(position=pos)
            return pos

    @property
    def heartbeat_task(self) -> Union[asyncio.Task, None]:
        """The `asyncio.Task` associated with the motor's heartbeat."""
        if self._heartbeat_task is None:
            self._heartbeat_task = []
            return
        elif len(self._heartbeat_task) == 0:
            return

        return self._heartbeat_task[0]

    @heartbeat_task.setter
    def heartbeat_task(self, val: asyncio.Task):
        if not isinstance(val, asyncio.Task):
            return
        elif self.heartbeat_task is None:
            pass
        elif self.heartbeat_task.done() or self.heartbeat_task.cancelled():
            # remove task from task list
            # self.tasks.remove(self.heartbeat_task)
            self._heartbeat_task = []
        else:
            # val is a new task and heartbeat is still running...stop old heartbeat
            self.loop.call_soon_threadsafe(self.heartbeat_task.cancel)
            # self.tasks.remove(self._heartbeat_task)

        self._heartbeat_task = [val]
        self.tasks.append(val)
        val.add_done_callback(self._heartbeat_task_done_callback)

    def _heartbeat_task_done_callback(self, task: asyncio.Task):
        """Callback to clean up references to the heartbeat task."""
        try:
            self.tasks.remove(task)
        except ValueError:
            pass

        if self.heartbeat_task is None:
            return

        try:
            self._heartbeat_task.remove(task)
        except ValueError:
            pass

    def start_heartbeat(self):
        """Start or restart the heartbeat `asyncio.Task`."""
        if (
            self.heartbeat_task is None
            or self.heartbeat_task.done()
            or self.heartbeat_task.cancelled()
        ):
            self.heartbeat_task = self.loop.create_task(self._heartbeat())

    def _update_status(self, **values):
        """
        Update ``self._status` dictionary with the given arguments ``**values``.
        """
        old_status = self.status.copy()
        new_status = {**old_status, **values}

        if dict_equal(old_status, new_status):
            return

        self._status = new_status
        self.signals.status_changed.emit()

    def connect(self):
        """
        Open the ethernet connection to the motor.  The number of
        reconnection attempts before an exception is raised is defined
        by ``self._setup["max_connection_attempts"]``.
        """
        if not isinstance(self.socket, socket.socket):
            # socket has not been created yet, self.socket is likely None
            pass
        else:
            try:
                socket_ip, socket_port = self.socket.getpeername()
            except OSError as err:
                self.logger.error(
                    "Appears the socket is bad.  It was likely disconnected by "
                    "the sever or the client.",
                    exc_info=err,
                )
            else:
                if self.ip != socket_ip or self.port != socket_port:
                    self.logger.error(
                        f"Socket IPv4 address {socket_ip}:{socket_port} does"
                        f" NOT match assigned IPv4 address {self.ip}:{self.port}.  "
                        f"Suspect improper re-assignment of address."
                    )
                    return
                elif self.socket.fileno() != -1:
                    # socket is created and running
                    return

        _allowed_attempts = self._setup["max_connection_attempts"]
        for _count in range(_allowed_attempts):
            try:
                msg = f"Connecting to {self.ip}:{self.port} ..."
                self.logger.info(msg)

                socket.setdefaulttimeout(3)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # 1 second timeout
                s.connect((self.ip, self.port))

                msg = "...SUCCESS!!!"
                self.logger.info(msg)
                self.socket = s
                self._update_status(connected=True)

                # connection established, break for-loop
                break
            except (
                TimeoutError,
                InterruptedError,
                ConnectionRefusedError,
                OSError,
                socket.timeout,
            ) as err:
                msg = f"...attempt {_count+1} of {_allowed_attempts} failed"
                if _count+1 < _allowed_attempts:
                    self.logger.warning(msg)
                else:
                    self.logger.error(msg)
                    self.logger.error(f"{err.__class__.__name__}: {err}")
                    # TODO: make this a custom exception (e.g. MotorConnectionError)
                    #       so other bapsf_motion functionality can respond
                    #       appropriately...the exception should likely inherit
                    #       from TimeoutError, InterruptedError, ConnectionRefusedError,
                    #       and socket.timeout
                    self._update_status(connected=False)
                    raise ConnectionError(
                        "Connection to motor could not be established."
                    )

        if self.loop is not None:
            self._configure_motor()
            self._get_motor_parameters()

    def _send_command(self, command, *args):
        """
        A low level method for sending commands to the motor, and
        receiving the response.
        """
        if self.loop.is_running() and (
            self.heartbeat_task is None
            or self.heartbeat_task.done()
            or self.heartbeat_task.cancelled()
        ):
            self.start_heartbeat()

        try:
            cmd_str = self._process_command(command, *args)
            recv_str = self._send_raw_command(cmd_str) if "?" not in cmd_str else cmd_str

            if recv_str == self.ack_flags.LOST_CONNECTION:
                raise ConnectionError("Lost connection to motor.")

            _rtn = self._process_command_return(command, *args, recv_str=recv_str)

        except (ConnectionError, TimeoutError, OSError) as err:
            # Note: if the Ack/Nack protocol is not properly set (see method
            #       read_and_set_protocol()), then TimeoutErrors can occur
            #       even if the connection is still established.
            #
            self.logger.error(
                f"Last command '{command}' was not executed.",
                exc_info=err,
            )

            _rtn = self.ack_flags.LOST_CONNECTION
            self._update_status(connected=False)

        return _rtn

    async def _send_command_async(self, command: str, *args):
        """A coroutine_ version of :meth:`_send_command`."""
        return self._send_command(command, *args)

    def send_command(self, command: str, *args, thread_id=None):
        """
        Send ``command`` to the motor, and receive its response.  If the
        `event loop`_ is running, then the command will be sent as
        a threadsafe coroutine_ in the loop.  Otherwise, the command
        will be sent directly to the motor.

        Parameters
        ----------
        command: str
            The desired command to be sent to the motor.
        *args:
            Any arguments to the ``command`` that will be sent with the
            motor command.
        thread_id: int
            ID of the thread the calling functionality is operating in.
        """
        if self.terminated:
            raise RuntimeError(
                f"Can not send command {command} to motor, since the "
                f"motor has been terminated."
            )

        if self._commands[command]["method_command"]:
            # execute respectively named method
            meth = getattr(self, command)
            return meth(*args)

        elif not self.loop.is_running():
            # event loop not running, just send commands directly
            return self._send_command(command, *args)

        elif (
            (thread_id is not None and threading.current_thread().ident == thread_id)
            or (threading.current_thread().ident == self._thread_id)
        ):
            # we are in the same thread as the running event loop, just
            # send the command directly
            tk = self.loop.create_task(self._send_command_async(command, *args))
            self.loop.run_until_complete(tk)
            return tk.result()

        # the event loop is running and the command is being sent from
        # outside the event loop thread
        future = asyncio.run_coroutine_threadsafe(
            self._send_command_async(command, *args),
            self.loop
        )
        return future.result(5)

    def _process_command(self, command: str, *args) -> str:
        """
        Process the command ``command`` and any input arguments
        ``*args`` to and return the full command string.  The
        argument processor is defined in the class attribute
        ``self._commands[command]["send_processor"]`` and the base
        command string is defined at
        ``self._commands[command]["send"]``.

        Parameters
        ----------
        command: str
            Command to be processed and sent to the motor
        args
            Argument for the base command.

        Returns
        -------
        str
            The full command string to be sent to the motor.

        Examples
        --------

        >>> self._process_command("speed", 5.5)
        "VE 5.5000"

        """
        cmd_dict = self._commands[command]
        cmd_str = cmd_dict["send"]

        processor = self._commands[command]["send_processor"]
        if processor is None:
            # If "send_processor" is None, then it is assumed no values
            # need to be sent with the command.
            if len(args):
                self.logger.error(
                    f"Command '{command}' requires 0 arguments to send, "
                    f"got {len(args)} arguments."
                )
            return cmd_str

        two_way = cmd_dict.get("two_way", False)
        if not len(args) and two_way:
            # command is being used as a getter instead of a setter
            return cmd_str
        elif not len(args):
            # command is acting as a setter without arguments
            self.logger.error(
                f"Command '{command}' is a setting command, but no "
                f"arguments were given."
            )
            return "?3"  # Nack code for too few parameters

        return cmd_str + processor(args[0])

    def _process_command_return_string(self, command: str, rtn_str: str) -> Any:
        """
        Process the returned string from the sent motor command.  The
        regular expression pattern for matching the returned string
        is defined in the class attribute
        ``self._commands[command]["recv"]`` and the argument processor
        is defined at ``self._commands[command]["recv_processor"]``.

        Parameters
        ----------
        command: str
            The command that was sent to the motor.
        rtn_str: str
            The string that was returned by the motor.

        Returns
        -------
        Any
            Returns the argument from the motor's response string.  The
            argument type is dependent on the receive processor
            ``self._commands[command]["recv_processor"]``.

        Examples
        --------

        >>> self._process_command_return_string("speed", "VE 5.500")
        5.5

        """

        _send_str = self._commands[command]["send"]

        if "%" in rtn_str:
            # Motor acknowledge and executed command.
            return self.ack_flags.ACK
        elif "*" in rtn_str:
            # Motor acknowledged command and buffered it into the queue
            return self.ack_flags.ACK_QUEUED
        elif "?" in rtn_str:
            # Motor negatively acknowledge command, error in command
            err_code = re.compile(
                r"\d?\?(?P<code>\d{1,2})"
            ).fullmatch(rtn_str).group("code")
            err_code = int(err_code)
            err_msg = f"{err_code} - {self._nack_codes[err_code]}"
            self.logger.error(
                f"Motor returned Nack from command {command} with error: {err_msg}."
            )
            return self.ack_flags.NACK
        elif not isinstance(rtn_str, str) or _send_str not in rtn_str:
            self.logger.error(
                f"The return string for command '{command} ({_send_str})'"
                f" is malformed, received '{rtn_str}'."
            )
            return self.ack_flags.MALFORMED

        recv_pattern = self._commands[command]["recv"]
        if recv_pattern is not None:
            rtn_str = recv_pattern.fullmatch(rtn_str).group("return")

        processor = self._commands[command]["recv_processor"]
        rtn = processor(rtn_str)

        units = self._commands[command]["units"]
        if units is not None:
            return rtn * units

        return rtn

    def _process_command_return(self, command: str, *args, recv_str: str) -> Any:
        _rtn = self._process_command_return_string(command, recv_str)

        if (
                len(args) == 0
                and (_rtn == self.ack_flags.ACK or _rtn == self.ack_flags.ACK_QUEUED)
                and self._commands[command]["recv"] is not None
        ):
            # command had NO arguments and expected a response with data
            # suspecting the command got buffered and acknowledge, and the
            # real data is coming in a followup communication
            _rtn = self.ack_flags.MALFORMED

        if _rtn != self.ack_flags.MALFORMED:
            return _rtn

        while _rtn == self.ack_flags.MALFORMED:
            # command and motor buffer have come out of sync
            #
            # Note:  this will not be an infinite loop, if the buffer
            #        size is zero, and we missed the response, then
            #        self._recv will issue a TimeoutError

            recv = self._recv()
            recv_str = recv.decode("ASCII")
            _rtn = self._process_command_return(command, *args, recv_str=recv_str)

        return _rtn

    def _send_raw_command(self, cmd: str):
        """
        Low-level functionality so a command string ``cmd` can be sent
        directly to the motor.  This is intended for testing purposes
        and should NOT be used for any high-level functionality.  This
        allows for sending commands that are ned defined in
        ``self._commands``.

        Parameters
        ----------
        cmd: str
            A desired command string that is sent to the motor.

        Returns
        -------
        str
            The "unmodified" return string from the motor.

        """
        self._send(cmd)

        try:
            return self._recv().decode("ASCII")
        except TimeoutError as err:
            self.logger.warning(
                f"Lost connection while trying to receive response to "
                f"commend '{cmd}'.",
                exc_info=err,
            )
            return self.ack_flags.LOST_CONNECTION

    def _send(self, cmd: str):
        """
        Low-level functionality to send a command string ``cmd`` to
        the motor.  Proper headers and end-of-message (eom) blocks are
        added to the command string.

        Parameters
        ----------
        cmd: str
            The command str to be sent to the motor.
        """
        # all messages sent or received over TCP/UDP for Applied Motion Motors
        # use a byte header b'\x00\x07' and end-of-message b'\r'
        # (carriage return)
        _header = b"\x00\x07"
        _eom = b"\r"  # end of message

        cmd_str = _header + bytes(cmd.encode("ASCII")) + _eom
        self.logger.debug(f"Sending command string '{cmd_str}'.")
        try:
            self.socket.sendall(cmd_str)
        except (ConnectionError, OSError) as err:
            self.logger.error(f"Unable to send command {cmd_str}.", exc_info=err)
            if err.errno == errno.EPIPE:
                self.logger.error(
                    "It appears the server (motor) has closed the connection."
                )
                self.socket.close()
            elif err.errno == errno.ESHUTDOWN:
                self.logger.error(
                    "It appears the socket has been closed."
                )
            elif err.errno == errno.EBADF:
                self.logger.error(
                    "The socket likely has not been created."
                )

            self.logger.info(
                "Attempting to re-establish connection and send the command "
                "again."
            )

            self._update_status(connected=False)
            self.connect()
            if self.connected:
                self.socket.sendall(cmd_str)

    def _recv(self) -> AnyStr:
        """
        Receives messages/strings from the motor.  Proper headers and
        end-of-message blocks are removed from the received string, and
        then returned.

        Returns
        -------
        byte string
            Trimmed byte string from the motor response.

        """
        # all messages sent or received over TCP/UDP for Applied Motion Motors
        # use a byte header b'\x00\x07' and end-of-message b'\r'
        # (carriage return)
        _header = b"\x00\x07"
        _eom = b"\r"  # end of message

        msg = b""
        while True:
            data = self.socket.recv(16)

            if not data:
                break
            elif not msg and _header in data:
                msg = data.split(_header)[1]
            else:
                msg += data

            if _eom in msg:
                msg = msg.split(_eom)[0]
                break

        self.logger.debug(f"Received string '{msg}'.")
        return msg

    def retrieve_motor_status(self, direct_send=False):
        """
        Retrieve motor status and update ``self._status``.

        Parameters
        ----------
        direct_send: bool
            If `True`, then the motor commands will bypass any active
            `event loop`_ and be directly sent to the motor.  If
            `False`, then all motor commands will be routed through the
            :meth:`send_command` method. (DEFAULT: `False`)

        """
        # TODO: How to document all the statuses that get updated with this method?
        #
        # this is done so self._heartbeat can directly send commands since
        # the heartbeat is already running in the event loop
        send_command = self._send_command if direct_send else self.send_command

        _rtn = send_command("request_status")
        if isinstance(_rtn, self.ack_flags):
            if _rtn == self.ack_flags.LOST_CONNECTION:
                return

            _rtn = ""
            _status = {}
        else:
            _status = {
                "alarm": False,
                "enabled": False,
                "fault": False,
                "moving": False,
                "homing": False,
                "jogging": False,
                "motion_in_progress": False,
                "in_position": False,
                "stopping": False,
                "waiting": False,
            }  # null status
        for letter in _rtn:
            if letter == "A":
                _status["alarm"] = True
            elif letter in ("D", "R"):
                _status["enabled"] = True if letter == "R" else False
            elif letter == "E":
                _status["fault"] = True
            elif letter == "F":
                _status["moving"] = True
            elif letter == "H":
                _status["homing"] = True
            elif letter == "J":
                _status["jogging"] = True
            elif letter == "M":
                _status["motion_in_progress"] = True
            elif letter == "P":
                _status["in_position"] = True
            elif letter == "S":
                _status["stopping"] = True
            elif letter in ("T", "W"):
                _status["waiting"] = True

        pos = send_command("get_position")
        if not isinstance(pos, self.ack_flags):
            _status["position"] = pos
        elif pos == self.ack_flags.LOST_CONNECTION:
            return

        alarm_status = self.retrieve_motor_alarm(
            defer_status_update=True,
            direct_send=direct_send,
        )
        if not isinstance(alarm_status, self.ack_flags):
            _status.update(alarm_status)
        elif alarm_status == self.ack_flags.LOST_CONNECTION:
            return

        if "moving" not in _status:
            pass
        elif _status["moving"] and not self._status["moving"]:
            self.signals.movement_started.emit()
        elif not _status["moving"] and self._status["moving"]:
            self.signals.movement_finished.emit()

        self._update_status(**_status)

    def retrieve_motor_alarm(
            self, defer_status_update=False, direct_send=False
    ) -> Union[Dict[str, Any], "AckFlags"]:
        """
        Retrieve [if any] motor alarm codes.

        Parameters
        ----------
        defer_status_update: bool
            If `True`, then do NOT update ``self._status``.
            (DEFAULT: `False`)

        direct_send: bool
            If `True`, then the motor commands will bypass any active
            `event loop`_ and be directly sent to the motor.  If
            `False`, then all motor commands will be routed through the
            :meth:`send_command` method. (DEFAULT: `False`)

        Returns
        -------
        Dict[str, Any]
            Alarm status.
        """
        # this is done so self._heartbeat can directly send commands since
        # the heartbeat is already running in the event loop
        send_command = self._send_command if direct_send else self.send_command

        send_command("alarm_reset")
        rtn = send_command("alarm")
        if isinstance(rtn, self.ack_flags):
            return rtn

        codes = []
        for i, digit in enumerate(rtn):
            integer = int(digit)
            codes.append(integer * 10**(3-i))

        alarm_message = []
        for code in codes:
            try:
                msg = self._alarm_codes[code]
                alarm_message.append(f"{code:04d} - {msg}")
            except KeyError:
                pass

        alarm_message = " :: ".join(alarm_message)

        if rtn != "0000":
            self.logger.error(f"Motor returned alarm(s): {alarm_message}")

        alarm_status = {
            "alarm": rtn != "0000",
            "alarm_message": alarm_message,
            "limits": {
                "CCW": True if 2 in codes else False,
                "CW": True if 4 in codes else False,
            },
        }

        if not defer_status_update:
            self._update_status(**alarm_status)

        return alarm_status

    def enable(self):
        """Enable motor (i.e. restore drive current to motor)."""
        self.send_command("enable")
        self.send_command("retrieve_motor_status")

    def disable(self):
        """Disable motor (i.e. reduce motor current to zero)."""
        self.send_command("disable")
        self.send_command("retrieve_motor_status")

    async def _heartbeat(self):
        """
        :ref:`Coroutine <coroutine>` for the heartbeat monitor of the
        motor.  The heartbeat will update the motor status via
        :meth:`retrieve_motor_status` at an interval given by
        :attr:`heartrate`.

        See Also
        --------
        retrieve_motor_status
        """
        old_HR = self.heartrate.BASE
        beats = 0
        while True:
            if self.terminated:
                # Motor is terminated or being terminated, so end the coroutine
                # immediately so the associated Task can be cancelled/stopped.
                continue
            elif self._pause_heartbeat:
                await asyncio.sleep(self.heartrate.PAUSE)
                continue
            elif not self.connected:
                heartrate = self.heartrate.SEARCHING
            elif self.is_moving:
                heartrate = self.heartrate.ACTIVE
            else:
                heartrate = self.heartrate.BASE

            if heartrate != old_HR:
                self.logger.info(
                    f"HR interval changed to {heartrate} sec - old HR beat {beats} times."
                )
                beats = 0

            if self.connected:
                self.retrieve_motor_status(direct_send=True)
            else:
                self.logger.info("Motor connection lost...trying to reconnect.")
                # Keep sending kill until the motor comes back online.  This will
                # ensure the motor is stopped and the buffer (queue) is empty, so
                # we can continue "safely" with new commands.
                self._send_command("kill")

            beats += 1
            old_HR = heartrate
            await asyncio.sleep(heartrate)

    def terminate(self, delay_loop_stop=False):
        self.logger.info("Terminating motor")

        # disconnect all signals before terminating
        self.signals.status_changed.disconnect_all()
        self.signals.movement_started.disconnect_all()
        self.signals.movement_finished.disconnect_all()

        if not self.terminated and self.connected:
            self.stop()
            self.disable()

        super().terminate(delay_loop_stop=delay_loop_stop)
        self._heartbeat_task = None

        try:
            self.socket.close()
        except AttributeError:
            pass

    def _moveable(self) -> bool:
        """
        Return `True` if a movement command can be sent to the motor.
        """
        if self.is_moving:
            return False

        if self.status["alarm"]:
            self.send_command("alarm_reset")
            alarm_status = self.retrieve_motor_alarm()
            alarm_messages = alarm_status["alarm_message"].split("::")

            self.logger.info(f"Alarm status: {alarm_status}")
            if (
                self._lost_connection(alarm_status)
                or len(alarm_messages) > 1
                or (
                    len(alarm_messages) == 1
                    and not alarm_status["limits"]["CCW"]
                    and not alarm_status["limits"]["CW"]
                )
            ):
                # lost connection or a non-limit alarm is active
                return False

        # alarm was successfully reset
        # or only the forward/backward limit is hit
        # or the motor is idle
        return True

    def continuous_jog(self, direction="forward"):
        """
        Start a continuous jog.  The motor will not stop until
        commanded to.
        """
        if direction not in ["forward", "backward"]:
            self.logger.error(
                "ValueError: Argument `direction` value must be 'forward' or 'backward'."
            )
            return

        if not self._moveable():
            alarm_msg = self.status["alarm_message"]
            self.logger.error(
                f"Motor alarm active, could not move. Alarm Status: {alarm_msg}"
            )
            return

        if self.status["alarm"]:
            # on a limit switch, check if move direction is off limit

            if direction == "forward" and self.status["limits"]["CW"]:
                self.logger.warning(
                    "Motor can NOT move forward, currently on forward limit."
                )
            elif direction == "backward" and self.status["limits"]["CCW"]:
                self.logger.warning(
                    "Motor can NOT move backward, currently on backward limit."
                )

        # The direction of the commence_jogging is defined by the side
        # of the target_distance (DI) command
        direction = -1 if direction == "backward" else 1
        self.enable()
        self.send_command("target_distance", direction)
        self.send_command("commence_jogging")

    def stop(self, soft=False):
        """Stop motor movement."""
        self.send_command("stop", soft)

    def move_to(self, pos: int):
        """
        Move the motor to a specified location.

        Parameters
        ----------
        pos: int
            Position (in steps) for the motor to move to.
        """
        if not self._moveable():
            alarm_msg = self.status["alarm_message"]
            self.logger.error(
                f"Motor alarm active, could not move. Alarm Status: {alarm_msg}"
            )
            return

        if self.status["alarm"]:
            # on a limit switch, check if move direction is off limit
            delta = pos - self.position.value

            if delta > 0 and self.status["limits"]["CW"]:
                self.logger.warning(
                    "Motor can NOT move forward, currently on forward limit."
                )
            elif delta < 0 and self.status["limits"]["CCW"]:
                self.logger.warning(
                    "Motor can NOT move backward, currently on backward limit."
                )

        # Note:  The Applied Motion Command Reference pdf states for
        #        ethernet enabled motors the position should not be
        #        given directly with the "feed" command.  The position
        #        must first be set with "target_distance" and then fed to
        #        position with "feed".
        self.enable()
        self.send_command("target_distance", pos)
        self.send_command("feed")
        self.send_command("retrieve_motor_status")

    def move_off_limit(self):
        """
        Move the motor off of a CW (forward) or CCW (backward) limit
        switch.
        """

        alarm_status = self.retrieve_motor_alarm()
        if (
            not alarm_status["alarm"]
            or (not alarm_status["limits"]["CCW"] and not alarm_status["limits"]["CW"])
        ):
            # not on limits
            return

        off_direction = -1 if self.status["limits"]["CW"] else 1

        counts = 1
        on_limits = any(self.status["limits"].values())
        switched_directions = False
        while on_limits:

            if counts > 10:
                self.logger.error(
                    "Moving off limits - Was not able to move of limit."
                )
                break

            pos = self.send_command("get_position")  # type: Union[u.Quantity, AckFlags]
            if self._lost_connection(pos):
                self.logger.error("Unable to move off limit due to a lost connection.")
                break
            elif pos == self.ack_flags.MALFORMED:
                counts += 1
                continue

            pos = pos.value
            move_to_pos = pos + off_direction * 0.5 * self.steps_per_rev.value
            self.move_to(move_to_pos)

            # wait until motor stops moving
            self.sleep(2 * self.heartrate.ACTIVE)
            while self.is_moving:
                self.sleep(self.heartrate.ACTIVE)

            alarm_msg = self.retrieve_motor_alarm(defer_status_update=True)
            if self._lost_connection(alarm_msg):
                self.logger.error("Unable to move off limit due to a lost connection.")
                break
            on_limits = any(alarm_msg["limits"].values())

            # reverse direction if motor did not move
            if np.isclose(self.position.value, pos):
                if switched_directions:
                    # off direction has already flipped once
                    self.logger.warning(
                        "Attempted to move off limit in both directions and "
                        "was unsuccessful."
                    )
                    break

                # no movement happened, try reversing direction
                off_direction = -off_direction
                switched_directions = True

            counts += 1

    @staticmethod
    async def _sleep_async(delay):
        """Asyncio coroutine so :meth:`sleep` can do an async sleep."""
        await asyncio.sleep(delay)

    def sleep(self, delay):
        """
        Sleep for X seconds defined by ``delay``.  The routine is smart
        enough to know if the event loop is running or not.  If the
        event loop is not running the sleep will be issued via
        `time.sleep`, otherwise it will leverage `asyncio.sleep`.

        Parameters
        ----------
        delay: ~numbers.Real
            Number of seconds to sleep.
        """
        if not self.loop.is_running():
            time.sleep(delay)
        elif threading.current_thread().ident == self._thread_id:
            tk = self.loop.create_task(self._sleep_async(delay))
            self.loop.run_until_complete(tk)

        future = asyncio.run_coroutine_threadsafe(
            self._sleep_async(delay),
            self.loop
        )
        future.result(5)

    def set_current(self, percent):
        r"""
        Set the peak current setting ("peak of sine") of the stepper
        drive, also known as the running current.  The value given
        is a fraction of 0-1 of the peak allowable current defined
        in  ``_motor["DEFAULTS"]["max_current"]``.

        Setting the running current can affect the idle current, since
        the max idle current is 90% of the running current.

        Parameters
        ----------
        percent: `float`
            A value of 0 - 1 specifying a fraction of the max running
            current to set the running current to.  For example,
            ``0.5`` will set the running current to 50% of the max
            allowable running current
            (``_motor["DEFAULTS"]["max_current"]``).
        """
        if not isinstance(percent, (int, float)):
            self.logger.error(
                f"Setting motor current, expected a value of 0 - 1 "
                f"but got type {type(percent)}."
            )
            return
        elif not (0 <= percent <= 1):
            self.logger.error(
                f"Setting motor current, expected a value of 0 - 1 "
                f"but got {percent}."
            )
            return

        new_cur = percent * self._motor["DEFAULTS"]["max_current"]

        ic = self.send_command("idle_current")
        if self._lost_connection(ic):
            self.logger.error("Unable to set current due to a lost connection.")
            return
        elif ic == self.ack_flags.MALFORMED:
            self.logger.error(
                "Unable to set current due to the motor response not matching "
                "the expected response."
            )
            return
        new_ic = np.min(
            [self._motor["DEFAULTS"]["max_idle_current"] * new_cur, ic],
        )

        self.send_command("current", new_cur)
        self.send_command("idle_current", new_ic)

    def set_idle_current(self, percent):
        r"""
        Set the motor's idle current.  The idle current is the current
        supplied to the stepper motors when the motor is not moving.
        The value given is a fraction 0 - 0.9 of the running current.

        Parameters
        ----------
        percent: `float`
            A value of 0 - 0.9 specifying a fraction of the running
            current to set the idle current to.  For example,
            ``0.5`` will set the idle current to 50% of the running
            current.
        """
        max_idle = self._motor["DEFAULTS"]["max_idle_current"]
        if not isinstance(percent, (int, float)):
            self.logger.error(
                f"Setting motor idle current, expected a value of 0 - {max_idle} "
                f"but got type {type(percent)}."
            )
            return
        elif not (0 <= percent <= max_idle):
            self.logger.warning(
                f"Setting motor idle current, expected a value of 0 - {max_idle} "
                f"but got {percent}.  Using {max_idle}."
            )
            percent = max_idle

        curr = self.send_command("current")
        if self._lost_connection(curr):
            self.logger.error("Unable to set idle current due to a lost connection.")
            return
        elif curr == self.ack_flags.MALFORMED:
            self.logger.error(
                "Unable to set idle current due to the motor response not "
                "matching the expected response."
            )
            return
        new_ic = percent * curr
        self.send_command("idle_current", new_ic)

    def reset_currents(self):
        """
        Reset running and idle currents to their default values.
        """
        max_curr = self._motor["DEFAULTS"]["max_current"]
        curr = self._motor["DEFAULTS"]["current"] * max_curr
        new_ic = self._motor["DEFAULTS"]["idle_current"] * curr

        self.send_command("current", curr)
        self.send_command("idle_current", new_ic)

    def set_position(self, pos):
        """
        Set current motor's absolute position to a value specified by
        ``pos``.

        pos: `int`
            An integer in the range of +/- 2,147,483,647 to set the
            motor's absolute position.
        """
        if not isinstance(pos, int):
            self.logger.error(
                f"Setting motor position, expect int between"
                f" +/- 2,147,483,647 but got type {type(pos)}."
            )
            return

        # set high torque
        ic = self.send_command("idle_current")
        if self._lost_connection(ic):
            self.logger.error("Unable to set position due to a lost connection.")
            return
        elif ic == self.ack_flags.MALFORMED:
            self.logger.error(
                "Unable to confirm set position due to the motor response "
                "not matching the expected response."
            )
            return

        curr = self.send_command("current")
        if self._lost_connection(curr):
            self.logger.error("Unable to set position due to a lost connection.")
            return
        elif curr == self.ack_flags.MALFORMED:
            self.logger.error(
                "Unable to confirm set position due to motor response "
                "not matching the expected response."
            )
            return

        # enable motor before zeroing so holding current is in effect
        enable_state = self.status["enabled"]
        self.send_command("enable")

        self.set_current(1)
        self.set_idle_current(self._motor["DEFAULTS"]["max_idle_current"])

        self.send_command("encoder_position", pos)
        self.send_command("set_position_SP", pos)

        self.send_command("current", curr)
        self.send_command("idle_current", ic)

        # return to previous enabled state
        if not enable_state:
            self.disable()

    def zero(self):
        """Define current motor position as zero."""
        self.set_position(0)
