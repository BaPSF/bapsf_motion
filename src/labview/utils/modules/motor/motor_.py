import time

from typing import Union

try:
    from bapsf_motion.actors import Motor
except ModuleNotFoundError:
    import sys

    from pathlib import Path

    _HERE = Path(__file__).resolve().parent
    _BAPSF_MOTION = (_HERE / ".." / ".." / ".." / "..").resolve()

    sys.path.append(str(_BAPSF_MOTION))

    from bapsf_motion.actors import Motor


MOTOR_NAME = "WALL-E"
_motor = None  # type: Union[Motor, None]


def _get_motor_object() -> Motor:
    if _motor is None:
        raise ValueError

    return _motor


def initialize(ip):
    mot = Motor(ip=ip, name=MOTOR_NAME, auto_start=True)
    globals()["_motor"] = mot


def move_to(pos) -> int:
    mot = _get_motor_object()
    mot.send_command("move_to", pos)

    time.sleep(0.2)
    while mot.is_moving:
        time.sleep(0.2)

    position = mot.position
    print(f"{MOTOR_NAME} stopped moving and is at position {position}.")

    return position


def cleanup():
    mot = _get_motor_object()
    mot.stop_running()
    globals()["_motor"] = None
