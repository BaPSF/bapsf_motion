import time

from typing import Union

try:
    from bapsf_motion.actors import Manager
except ModuleNotFoundError:
    import sys

    from pathlib import Path

    _HERE = Path(__file__).resolve().parent
    _BAPSF_MOTION = (_HERE / "..").resolve()

    sys.path.append(str(_BAPSF_MOTION))

    from bapsf_motion.actors import Manager


MANAGER_NAME = "COO"
_manager = None  # type: Union[Motor, None]


def _get_manager_obj() -> Manager:
    if _manager is None:
        raise ValueError

    return _manager


def initialize(config):
    man = Manager(config, auto_run=True)
    globals()["_manager"] = man


def move_to(pos) -> int:
    man = _get_manager_obj()
    man.send_command("move_to", pos)

    time.sleep(0.2)
    while man.is_moving:
        time.sleep(0.2)

    position = man.position
    print(f"{MANAGER_NAME} stopped moving and is at position {position}.")

    return position


def cleanup():
    man = _get_manager_obj()
    man.stop_running()
    globals()["_motor"] = None
