
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
    format="%(asctime)s - [%(levelname)s] %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
    force=True,
)
logger = logging.getLogger(":: Interface ::")

MANAGER_NAME = "RM"
_rm = None  # type: Union[RunManager, None]


# TODO:  create a decorator to catch Exceptions, record them to the log,
#        and prevent them from being raised...LV can not communicate to
#        the python session once an exception is raised
# TODO:  Add logging entries when each of the interface request
#        functions is called

def _get_run_manager() -> RunManager:
    if _rm is None:
        raise ValueError

    return _rm


def get_config(filename):
    logger.debug("Received 'get_config' request.")
    from bapsf_motion.utils import load_example

    return load_example(filename, as_string=True)


def load_config(config):
    logger.debug("Received 'load_config' request.")
    rm = RunManager(config, auto_run=True)
    globals()["_rm"] = rm


def move_to_index(index):
    logger.debug(f"Received 'move_to_index' ({index}) request.")
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
    logger.debug(f"Received 'get_max_motion_list_size' request.")
    rm = _get_run_manager()

    ml_sizes = []
    for mg in rm.mgs.values():
        ml_sizes.append(mg.mb.motion_list.shape[0])

    return max(ml_sizes)


def cleanup():
    logger.debug(f"Received 'cleanup' request.")
    rm = _get_run_manager()
    rm.terminate()
    del globals()["_rm"]
