
import functools
import logging
import multiprocessing as mp
import time

from collections import UserDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Union

try:
    from bapsf_motion.actors import RunManager
    from bapsf_motion.utils import toml
except ModuleNotFoundError:
    import sys

    from pathlib import Path

    _HERE = Path(__file__).resolve().parent
    _BAPSF_MOTION = (_HERE / "..").resolve()

    sys.path.append(str(_BAPSF_MOTION))

    from bapsf_motion.actors import RunManager
    from bapsf_motion.utils import toml

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


def catch_and_log(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except Warning as err:
            logger.warning(f"Python threw the following warning: {err}.")
        except Exception as err:
            logger.error(f"Python threw the following exception: {err}.")

    return wrapper


@catch_and_log
def get_config(filename):
    logger.debug("Received 'get_config' request.")
    from bapsf_motion.utils import load_example

    return load_example(filename, as_string=True)


@catch_and_log
def load_config(config):
    logger.debug("Received 'load_config' request.")
    rm = RunManager(config, auto_run=True)
    globals()["_rm"] = rm


@catch_and_log
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


@catch_and_log
def get_max_motion_list_size() -> int:
    """Get the size of the largest motion list in the data run."""
    logger.debug(f"Received 'get_max_motion_list_size' request.")
    rm = _get_run_manager()

    ml_sizes = []
    for mg in rm.mgs.values():
        ml_sizes.append(mg.mb.motion_list.shape[0])

    return max(ml_sizes)


@catch_and_log
def cleanup():
    logger.debug(f"Received 'cleanup' request.")
    rm = _get_run_manager()
    rm.terminate()
    del globals()["_rm"]


def _deepcopy_dict(item):
    _copy = {}
    for key, val in item.items():
        if isinstance(val, (dict, UserDict)):
            val = _deepcopy_dict(val)

        _copy[key] = val

    return _copy


def as_toml_string(config) -> str:
    def convert_key_to_string(_d):
        _config = {}
        for key, value in _d.items():
            if isinstance(value, (dict, UserDict)):
                value = convert_key_to_string(value)

            if not isinstance(key, str):
                key = f"{key}"

            _config[key] = value

        return _config

    config_str = toml.dumps(convert_key_to_string(config))
    if not config_str.startswith("[run]"):
        config_str = "[run]\n" + config_str

    return config_str


def _run_configure(lock: mp.Lock, config: Dict[str, Any]):
    from PySide6.QtWidgets import QApplication
    from bapsf_motion import __version__
    from bapsf_motion.gui.configure import ConfigureGUI

    lock.acquire()

    app = QApplication([])
    window = ConfigureGUI()
    window.show()
    app.exec()

    config.update(_deepcopy_dict(window.rm.config))
    config["BAPSF_MOTION_VERSION"] = __version__

    lock.release()


def configure():
    mp.set_executable(
        (_HERE / ".venv" / "bin" / "python").resolve()
    )
    mp.set_start_method("spawn")
    lock = mp.Lock()
    with mp.Manager() as manager:
        data = manager.dict()
        p = mp.Process(target=_run_configure, args=(lock, data))
        p.start()
        p.join()

        logger.info(f"The run configurator finished with exit code {p.exitcode}.")

        if p.exitcode == 0:
            config_str = as_toml_string(data)
            logger.info(f"The run configurator returned a configuration of {config_str}.")
        else:
            logger.error(
                f"The run configurator returned with an exit code of {p.exitcode}."
            )
            config_str = ""

    return config_str
