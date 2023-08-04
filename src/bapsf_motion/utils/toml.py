"""Module for TOML file functionality."""
__all__ = []

import sys

from tomli_w import *
from tomli_w import __all__ as __rall__

if sys.version_info < (3, 11):   # coverage: ignore
    from tomli import *
    from tomli import __all__ as __wall__
else:
    from tomllib import *
    from tomllib import __all__ as __wall__

__all__ += __rall__
__all__ += __wall__

del sys, __rall__, __wall__
