"""
Module containing all the elements for the Configuration GUI.
"""

__all__ = ["ConfigureGUI"]

from bapsf_motion.gui.configure.configure_ import ConfigureGUI

if __name__ == "__main__":
    import argparse
    import os
    import pathlib

    # from PySide6.QtWidgets import QApplication
    from bapsf_motion.gui.configure.configure_ import ConfigureApp

    parser = argparse.ArgumentParser(
        description="Launch the bapsf_motion Configuration GUI (ConfigureGUI)",
    )
    parser.add_argument(
        "-d",
        "--defaults-file",
        help="Path to the TOML defaults file that contains pre-defined configurations.",
        default=(pathlib.Path.cwd() / "bapsf_motion.toml").resolve(),
        type=pathlib.Path,
    )
    parser.add_argument(
        "-c",
        "--config-file",
        help="Path to a TOML run configuration file",
        default=None,
        type=pathlib.Path,
    )
    default_debug = (
            "*.debug=true;"
            "qt.text.emojisegmenter.debug=false;"
            "qt.widgets.showhide.debug=false"
        )
    parser.add_argument(
        "--debug",
        nargs="?",
        const=default_debug,
        type=str,
        default=None,
        help=(
            "Sets the QT_LOGGING_RULES environment variable.  If not "
            f"specified, then will default to '{default_debug}'."
        ),
    )
    args = parser.parse_args()

    # Hanlde --default-file
    if args.defaults_file is not None and not args.defaults_file.exists():
        args.defaults_file = None
    elif args.defaults_file is not None:
        args.defaults_file = args.defaults_file.resolve()

    # Hanlde --config-file
    if args.config_file is not None and not args.config_file.exists():
        args.config_file = None
    elif args.config_file is not None:
        args.config_file = args.config_file.resolve()

    # Hanlde --debug
    if args.debug is not None:
        os.environ["SHIBOKEN_DEBUG"] = "1"
        os.environ["QT_DEBUG_PLUGINS"] = "1"
        os.environ["QT_LOGGING_RULES"] = args.debug

    # Launch App
    app = ConfigureApp(
        [],
        config=args.config_file,
        defaults=args.defaults_file,
    )
    app.exec()
