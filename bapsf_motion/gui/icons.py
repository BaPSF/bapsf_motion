"""
A collection of functionality focused around build and managing icon
widgets.
"""

__all__ = ["icon_name_dict"]

from bapsf_qt.utils import icon_name_dict

# add left and right arrows ... this needs to be piped to bapsf_qt
family = icon_name_dict["arrow-down"].split(".")[0]
icon_name_dict.update(
    {
        "arrow-left": f"{family}.arrow-left",
        "arrow-right": f"{family}.arrow-right",
        "park": "ri.parking-box-line",
        "park-solid": "ri.parking-box-fill",
        "robot-dead": "mdi.robot-dead-outline",
        "wifi-offline": "ri.wifi-off-line",
        "wifi-online": "ri.wifi-line",
    }
)
