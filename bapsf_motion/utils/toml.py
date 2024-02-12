"""
Module for TOML file functionality.

TOMl functionality exists in different 3rd party packages and builtin
packages across Python versions.  This module is intended to import
the appropriate packages based on the Python environment version and
name wrangle the functionality to provide a consistent interface for
`bapsf_motion`.
"""
__all__ = []

import sys

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

del sys, __rall__, __wall__
