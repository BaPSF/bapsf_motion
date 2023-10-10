import time

from typing import Union

try:
    from bapsf_motion.actors import RunManager
except ModuleNotFoundError:
    import sys

    from pathlib import Path

    _HERE = Path(__file__).resolve().parent
    _BAPSF_MOTION = (_HERE / "..").resolve()

    sys.path.append(str(_BAPSF_MOTION))

    from bapsf_motion.actors import RunManager


MANAGER_NAME = "RM"
_rm = None  # type: Union[RunManager, None]


def _get_run_manager() -> RunManager:
    if _rm is None:
        raise ValueError

    return _rm


def get_config(filename):
    from bapsf_motion.utils import load_example

    return load_example(filename, as_string=True)


def load_config(config):
    rm = RunManager(config, auto_run=True)
    globals()["_rm"] = rm


def move_to(mg_key, pos) -> int:
    rm = _get_run_manager()
    rm.mgs[mg_key].move_to(pos)

    time.sleep(0.2)
    while rm.is_moving:
        time.sleep(0.2)

    position = rm.position
    print(f"{MANAGER_NAME} stopped moving and is at position {position}.")

    return position


def cleanup():
    rm = _get_run_manager()
    rm.terminate()
    del globals()["_rm"]
