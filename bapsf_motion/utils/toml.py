"""
Module for TOML file functionality.

TOMl functionality exists in different 3rd party packages and builtin
packages across Python versions.  This module is intended to import
the appropriate packages based on the Python environment version and
name wrangle the functionality to provide a consistent interface for
`bapsf_motion`.
"""
__all__ = ["as_toml_string"]

import sys

from collections import UserDict
from tomli_w import *
from tomli_w import __all__ as __rall__

if sys.version_info < (3, 11):
    # noqa
    from tomli import *
    from tomli import __all__ as __wall__
else:
    # noqa
    # tomllib is a builtin package for py3.11+
    from tomllib import *
    from tomllib import __all__ as __wall__

__all__ += __rall__
__all__ += __wall__


def as_toml_string(config):
    """
    Iterate through a configuration dictionary and convert all keys to
    strings.  This is required because `dumps` can not handle non-string
    keys.
    """
    def convert_key_to_string(_d):
        _config = {}
        for key, value in _d.items():
            if isinstance(value, (dict, UserDict)):
                value = convert_key_to_string(value)

            if not isinstance(key, str):
                key = f"{key}"

            _config[key] = value

        return _config

    return dumps(convert_key_to_string(config))


# cleanup namespace
del sys, __rall__, __wall__
