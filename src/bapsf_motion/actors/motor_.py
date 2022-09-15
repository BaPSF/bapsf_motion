
__all__ = ["Motor"]

import asyncio
import logging
import re
import socket
import threading
import time

from collections import namedtuple
from typing import Any, Dict, List, Optional

from bapsf_motion.utils import ipv4_pattern, SimpleSignal


class Motor:
    # : parameters that define the setup of the Motor class (actual motor settings
    # should be defined in _motor)
    _setup = {
        "name": "",
        "logger": None,
        "loop": None,
        "thread": None,
        "socket": None,
        "tasks": None,
        "max_connection_attempts": 3,
        "heartrate": namedtuple("HR", ["base", "active"])(
            base=2, active=0.2
        ),  # in seconds
        "port": 7776,  # 7776 is Applied Motion's TCP port, 7775 is the UDP port
    }    # type: Dict[str, Any]

    #: these are setting that determine the motor parameters
    _motor = {
        "ip": None,
        "manufacturer": "Applied Motion Products",
        "model": "STM23S-3EE",
        "gearing": None,  # steps/rev
        "encoder_resolution": None,  # counts/rev
        "DEFAULTS": {
            "speed": 12.5,
            "accel": 25,
            "decel": 25,
        },
        "speed": None,
        "accel": None,
        "decel": None,
        "protocol_settings": None,
    }  # type: Dict[str, Any]

    #: these are parameters that define the current state of the motor
    _status = {
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
    }  # type: Dict[str, Any]

    #: simple signal to tell handlers that _status changed
    status_changed = SimpleSignal()
    movement_started = SimpleSignal()
    movement_finished = SimpleSignal()

    #: available commands that can be sent to the motor
    _commands = {
        "acceleration": {
            "send": "AC",
            "send_processor": lambda value: f"{float(value):.3f}",
            "recv": re.compile(r"AC=(?P<return>[0-9]+\.?[0-9]*)"),
            "recv_processor": float,
            "two_way": True,
        },
        "alarm": {
            "send": "AL",
            "recv": re.compile(r"AL=(?P<return>[0-9]{4})"),
        },
        "alarm_reset": {
            "senf": "AR",
            "recv": None,
        },
        "deceleration": {
            "send": "DE",
            "send_processor": lambda value: f"{float(value):.3f}",
            "recv": re.compile(r"DE=(?P<return>[0-9]+\.?[0-9]*)"),
            "recv_processor": float,
            "two_way": True,
        },
        "disable": {"send": "MD", "recv": None},
        "enable": {"send": "ME", "recv": None},
        "encoder_resolution": {
            "send": "ER",
            "recv": re.compile(r"ER=(?P<return>[0-9]+)"),
            "recv_processor": int,
        },
        "feed": {
            "send": "FP",
            "recv": None,
        },
        "gearing": {
            "send": "EG",
            "recv": re.compile(r"EG=(?P<return>[0-9]+)"),
            "recv_processor": int,
        },
        "get_position": {
            "send": "IP",
            "recv": re.compile(r"IP=(?P<return>-?[0-9]+)"),
            "recv_processor": int,
        },
        "move_to": None,
        "protocol": {
            "send": "PR",
            "send_processor": lambda value: f"{int(value)}",
            "recv": re.compile(r"PR=(?P<return>[0-9]{1,3})"),
            "recv_processor": int,
            "two_way": True,
        },
        "request_status": {
            "send": "RS",
            "recv": re.compile(r"RS=(?P<return>[ADEFHJMPRSTW]+)"),
        },
        "retrieve_motor_alarm": None,
        "retrieve_motor_status": None,
        "speed": {
            "send": "VE",
            "send_processor": lambda value: f"{float(value):.4f}",
            "recv": re.compile(r"VE=(?P<return>[0-9]+\.?[0-9]*)"),
            "recv_processor": float,
            "two_way": True,
        },
        "stop": {"send": "SK", "recv": None},
        "target_distance": {
            "send": "DI",
            "send_processor": lambda value: f"{int(value)}",
            "recv": re.compile(r"DI=(?P<return>[0-9]+)"),
            "recv_processor": int,
            "two_way": True,
        },
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

    # TODO: determine why heartbeat is not beating during a move
    #       - above statement is not true, but the heartbeat seems
    #         slower than the specified HR
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

    def __init__(
        self,
        *,
        ip: str,
        name: str = None,
        logger=None,
        loop=None,
        auto_start=False,
    ):
        self.setup_logger(logger, name)
        self.ip = ip
        self.connect()

        # loop needs to be setup before any commands are sent to the motor
        self.setup_event_loop(loop)

        self._get_motor_parameters()
        self._configure_motor()
        self.send_command("retrieve_motor_status")

        if auto_start:
            self.run()

    def _configure_motor(self):
        self._send_raw_command("IFD")  # set format of immediate commands to decimal

        # ensure motor always sends Ack/Nack
        self._read_and_set_protocol()

    def _read_and_set_protocol(self):
        rtn = self.send_command("protocol")
        _bits = f"{rtn:09b}"

        if _bits[-3] == "0":
            _bits = list(_bits)
            _bits[-3] = "1"  # sets always ack/nack
            _bits = "".join(_bits)
            _bits = int(_bits, 2)
            self.send_command("protocol", _bits)

            rtn = self.send_command("protocol")
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
    def name(self):
        return self._setup["name"]

    @name.setter
    def name(self, value):
        self._setup["name"] = value

    @property
    def logger(self) -> logging.Logger:
        return self._setup["logger"]

    @logger.setter
    def logger(self, value):
        self._setup["logger"] = value

    @property
    def _loop(self) -> asyncio.events.AbstractEventLoop:
        return self._setup["loop"]

    @_loop.setter
    def _loop(self, value):
        self._setup["loop"] = value

    @property
    def _thread(self):
        return self._setup["thread"]

    @_thread.setter
    def _thread(self, value):
        self._setup["thread"] = value

    @property
    def heartrate(self):
        return self._setup["heartrate"]

    @property
    def status(self):
        return self._status

    @property
    def ip(self):
        return self._motor["ip"]

    @ip.setter
    def ip(self, value):
        if ipv4_pattern.fullmatch(value) is None:
            raise ValueError(f"Supplied IP address ({value}) is not a valid IPv4.")

        self._motor["ip"] = value

    @property
    def port(self):
        return self._setup["port"]

    @property
    def socket(self) -> socket.socket:
        return self._setup["socket"]

    @socket.setter
    def socket(self, value):
        if not isinstance(value, socket.socket):
            raise TypeError(f"Expected type {socket.socket}, got type {type(value)}.")

        self._setup["socket"] = value

    @property
    def tasks(self) -> List[asyncio.Task]:
        if self._setup["tasks"] is None:
            self._setup["tasks"] = []

        return self._setup["tasks"]

    @property
    def is_moving(self):
        is_moving = self.status["moving"]
        if is_moving is None:
            return False
        return is_moving

    @property
    def position(self):
        pos = self.send_command("get_position")
        self.update_status(position=pos)
        return pos

    def update_status(self, **values):
        old_status = self.status.copy()
        new_status = {**old_status, **values}
        changed = {}
        for key, value in new_status.items():
            if key not in old_status or (key in old_status and old_status[key] != value):
                changed[key] = value

        if changed:
            self.logger.debug(f"Motor status changed, new values are {changed}.")
            self.status_changed.emit(True)

        self._status = new_status

    def setup_logger(self, logger, name):
        log_name = __name__ if logger is None else logger.name
        if name is not None:
            log_name += f".{name}"
            self.name = name
        self.logger = logging.getLogger(log_name)

    def setup_event_loop(self, loop):
        # 1. loop is given and running
        #    - store loop
        #    - add tasks
        # 2. loop is given and not running
        #    - store loop
        #    - add tasks
        # 3. loop is NOT given
        #    - create new loop
        #    - store loop
        #    - add tasks
        # get a valid event loop
        if loop is None:
            loop = asyncio.new_event_loop()
        elif not isinstance(loop, asyncio.events.AbstractEventLoop):
            self.logger.warning(
                "Given asyncio event is not valid.  Creating a new event loop to use."
            )
            loop = asyncio.new_event_loop()
        self._loop = loop

        # populate loop with tasks
        task = self._loop.create_task(self._heartbeat())
        self.tasks.append(task)

    def connect(self):
        _allowed_attempts = self._setup["max_connection_attempts"]
        for _count in range(_allowed_attempts):
            try:
                msg = f"Connecting to {self.ip}:{self.port} ..."
                self.logger.debug(msg)

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)  # 1 second timeout
                s.connect((self.ip, self.port))

                msg = "...SUCCESS!!!"
                self.logger.debug(msg)
                self.socket = s
                self.update_status(connected=True)
                return
            except (
                TimeoutError,
                InterruptedError,
                ConnectionRefusedError,
                socket.timeout,
            ) as error_:
                msg = f"...attempt {_count+1} of {_allowed_attempts} failed"
                if _count+1 < _allowed_attempts:
                    self.logger.warning(msg)
                else:
                    self.logger.error(msg)
                    raise error_

    def _send_command(self, command, *args):
        cmd_str = self._process_command(command, *args)
        recv_str = self._send_raw_command(cmd_str) if "?" not in cmd_str else cmd_str
        return self._process_command_return(command, recv_str)

    async def _send_command_async(self, command, *args):
        return self._send_command(command, *args)

    def send_command(self, command, *args):
        if self._commands[command] is None:
            # execute respectively named method
            meth = getattr(self, command)
            return meth(*args)

        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._send_command_async(command, *args),
                self._loop
            )
            return future.result(5)
        return self._send_command(command, *args)

    def _process_command(self, command: str, *args):
        cmd_dict = self._commands[command]
        cmd_str = cmd_dict["send"]

        try:
            processor = self._commands[command]["send_processor"]
        except KeyError:
            # If the "send_processor" key is not defined, then it is
            # assumed no values need to be sent with the command.
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

    def _process_command_return(self, command: str, rtn_str: str):

        if "%" in rtn_str:
            # Motor acknowledge and executed command.
            return rtn_str
        elif "*" in rtn_str:
            # Motor acknowledged command and buffered it into the queue
            return rtn_str
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
            return rtn_str

        recv_pattern = self._commands[command]["recv"]
        if recv_pattern is not None:
            rtn_str = recv_pattern.fullmatch(rtn_str).group("return")

        try:
            processor = self._commands[command]["recv_processor"]
            return processor(rtn_str)
        except KeyError:
            # If the "recv_processor" key is not defined, then it is
            # assumed the string is just to be passed back.
            return rtn_str

    def _send_raw_command(self, cmd: str):
        self._send(cmd)
        data = self._recv()
        return data.decode("ASCII")

    def _send(self, cmd: str):
        # all messages sent or received over TCP/UDP for Applied Motion Motors
        # use a byte header b'\x00\x07' and end-of-message b'\r'
        # (carriage return)
        _header = b"\x00\x07"
        _eom = b"\r"  # end of message

        cmd_str = _header + bytes(cmd.encode("ASCII")) + _eom
        try:
            self.socket.send(cmd_str)
        except ConnectionError:
            self.update_status(connected=False)
            self.connect()
            self.socket.send(cmd_str)

    def _recv(self):
        # all messages sent or received over TCP/UDP for Applied Motion Motors
        # use a byte header b'\x00\x07' and end-of-message b'\r'
        # (carriage return)
        _header = b"\x00\x07"
        _eom = b"\r"  # end of message

        msg = b""
        while True:
            data = self.socket.recv(16)

            if not msg and _header in data:
                msg = data.split(_header)[1]
            else:
                msg += data

            if _eom in msg:
                msg = msg.split(_eom)[0]
                break

        return msg

    def retrieve_motor_status(self, direct_send=False):
        # this is done so self._heartbeat can directly send commands since
        # the heartbeat is already running in the event loop
        send_command = self._send_command if direct_send else self.send_command

        _rtn = send_command("request_status")
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
        _status["position"] = pos

        if _status["alarm"]:
            _status["alarm_message"] = self.retrieve_motor_alarm(
                defer_status_update=True,
                direct_send=True,
            )

        if _status["moving"] and not self._status["moving"]:
            self.movement_started.emit(True)
        elif not _status["moving"] and self._status["moving"]:
            self.movement_finished.emit(True)

        self.update_status(**_status)

    def retrieve_motor_alarm(self, defer_status_update=False, direct_send=False):
        # this is done so self._heartbeat can directly send commands since
        # the heartbeat is already running in the event loop
        send_command = self._send_command if direct_send else self.send_command

        rtn = send_command("alarm")

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

        if alarm_message:
            self.logger.error(f"Motor returned alarm(s): {alarm_message}")

        if not defer_status_update and alarm_message:
            self.update_status(alarm_message=alarm_message)

        return alarm_message

    def enable(self):
        self.send_command("enable")
        self.send_command("retrieve_motor_status")

    def disable(self):
        self.send_command("disable")
        self.send_command("retrieve_motor_status")

    async def _heartbeat(self):
        old_HR = self.heartrate.base
        beats = 0
        while True:
            heartrate = self.heartrate.active if self.is_moving else self.heartrate.base

            if heartrate != old_HR:
                self.logger.info(
                    f"HR interval changed to {heartrate} sec - old HR beat {beats} times."
                )
                beats = 0

            self.retrieve_motor_status(direct_send=True)
            # self.logger.debug("Beat status.")

            beats += 1
            old_HR = heartrate
            await asyncio.sleep(heartrate)

    def run(self):
        if self._loop.is_running():
            return

        self._thread = threading.Thread(target=self._loop.run_forever)
        self._thread.start()

    def stop_running(self):
        for task in list(self.tasks):
            task.cancel()
            self.tasks.remove(task)

        try:
            self.socket.close()
        except AttributeError:
            pass

        self._loop.call_soon_threadsafe(self._loop.stop)

    def stop(self):
        self.send_command("stop")

    def move_to(self, pos):
        if self.status["alarm"]:
            self.send_command("alarm_rest")
            time.sleep(1.2 * self.heartrate.active)

            if self.status["alarm"]:
                self.logger.error("Motor alarm could not be rest.")
                return

        # Note:  The Applied Motion Command Reference pdf states for
        #        ethernet enabled motors the position should not be
        #        given directly with the "feed" command.  The position
        #        must first be set with "target_distance" and then fed to
        #        position with "feed".
        self.enable()
        self.send_command("target_distance", pos)
        self.send_command("feed")
        self.send_command("retrieve_motor_status")
