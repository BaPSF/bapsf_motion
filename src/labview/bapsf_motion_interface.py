
import logging
import time

from datetime import datetime, timedelta
from pathlib import Path
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

_HERE = Path(__file__).resolve().parent
_LOG_FILE = (_HERE / "run.log").resolve()
logging.basicConfig(
    filename=_LOG_FILE,
    filemode="w",
    format="%(asctime)s -[%(levelname)s] %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
    force=True,
)

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


def move_to_index(index):
    rm = _get_run_manager()

    for mg in rm.mgs.values():
        try:
            mg.move_ml(index)
        except ValueError as err:
            mg.logger.warning(
                f"Motion list index {index} is out of range. NO MOTION DONE. [{err}]."
            )
            pass

    wait_until = datetime.now() + timedelta(seconds=20)
    timeout = False
    time.sleep(.5)
    while rm.is_moving or timeout:
        time.sleep(.5)

        if wait_until < datetime.now():
            timeout = True

    if timeout:
        for mg in rm.mgs.values():
            mg.stop()

        raise RuntimeWarning(
            "Probe movement did not complete within the timeout restrictions.  "
            "Check drives and try again."
        )


def get_max_motion_list_size() -> int:
    """Get the size of the largest motion list in the data run."""
    rm = _get_run_manager()

    ml_sizes = []
    for mg in rm.mgs.values():
        ml_sizes.append(mg.mb.motion_list.shape[0])

    return max(ml_sizes)


def cleanup():
    rm = _get_run_manager()
    rm.terminate()
    del globals()["_rm"]
