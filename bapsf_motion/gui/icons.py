"""
A collection of functionality focused around build and managing icon
widgets.
"""
__all__ = ["icon_name_dict"]

import qtawesome as qta

from packaging.version import Version


def _build_icon_name_dictionary():
    family = "fa" if Version(qta.__version__) < Version("1.4") else "fa6s"

    icon_names = {
        "arrow-down": f"{family}.arrow-down",
        "arrow-up": f"{family}.arrow-up",
        "gear": f"{family}.gear",
        "question-circle": f"{family}.question-circle-o",
        "window-close": "fa5.window-close",
        "check-circle": "fa5.check-circle",
        "exchange-alt": "fa5s.exchange-alt",
    }
    if family == "fa":
        icon_names["question-circle"] = "fa.question-circle-o"
    else:
        icon_names["question-circle"] = "fa5.question-circle"

    return icon_names


icon_name_dict = _build_icon_name_dictionary()
"""Dictionary mapping simple icon names to `qtawesome` icon names."""
