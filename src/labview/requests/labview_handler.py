# Note: runtherun was purposely deleted...this should be be replaced
#       with bapsf_motion.actors.Manager when the code is developed
from bapsf_motion.runtherun import RunManager

RunManager = RunManager()


# define wrapper for LabVIEW Python node
def labview_handler(request, *args, **kwargs):
    _requests = {
        "connect": lv_handle_connect,
        "move_to_index": lv_handle_move_to,
        "stop": lv_handle_stop,
        "heartbeat": lv_handle_heartbeat,
        "set_velocity": lv_handle_velocity,
        "disconnect": lv_handle_disconnect,
        "configure": lv_handle_configure,
        "get_int_names": lv_handle_getintname,
        "get_integers": lv_handle_getint,
        "device_request": lv_handle_device_request,
    }
    return _requests[request](*args, **kwargs)


def lv_handle_connect(filename=None, config=None):
    return RunManager.__init__(filename, config)


def lv_handle_device_request(request):
    pass


def lv_handle_move_to(index):
    return RunManager.move_to_index(index)


def lv_handle_stop(group, everything=False):
    return RunManager.stop(group, everything)


def lv_handle_heartbeat(group):
    return RunManager.heartbeat(group)


def lv_handle_velocity(group, vx=1, vy=1, vz=1, everything=False):
    return RunManager.set_velocity(group, vx, vy, vz, everything)


def lv_handle_disconnect(group, everything=False):
    return RunManager.disconnect(group, everything)


def lv_handle_configure():

    return


def lv_handle_getconfig():
    return RunManager.config


def lv_handle_getint(request):
    if request == "last index":
        return RunManager.index


def lv_handle_getintname():
    return "last index"
