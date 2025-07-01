"""Subpackage containing GUI's for `bapsf_motion`."""
__all__ = [
    "ConfigureApp",
    "LaPDXYTransformCalculator",
    "LaPDXYTransformCalculatorApp",
    "get_qapplication",
    "get_color_scheme",
    "cast_color_to_rgba_string",
]

try:
    from bapsf_motion.gui.configure.configure_ import ConfigureApp
    from bapsf_motion.gui.helpers import (
        get_qapplication,
        get_color_scheme,
        cast_color_to_rgba_string,
    )
    from bapsf_motion.gui.lapd_xy_transform_calculator import (
        LaPDXYTransformCalculator,
        LaPDXYTransformCalculatorApp
    )
except (ModuleNotFoundError, ImportError) as err:
    msg = (
        f"{err.msg} ... It is likely GUI dependencies were not installed.  "
        f"Install bapsf_motion with the gui option, "
        f"'pip install bapsf_motion[gui]'."
    )
    err.msg = msg
    raise
