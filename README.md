# bapsfdaq_motion

[![Documentation Status](https://readthedocs.org/projects/bapsfdaq-motion/badge/?version=latest)](https://bapsfdaq-motion.readthedocs.io/en/latest/?badge=latest)

``bapsfdaq_motion`` is a module developed for the 
[Basic Plasma Facility (BaPSF)](https://plasma.physics.ucla.edu/) at the
University of California, Los Angeles to integrate with its DAQ system
and control motion devices, such as probe drives.

## GUI Development

This package uses ``PySide6`` to develop its GUI interface.  In attempts
to keep the code pythonic, we are using the feature
[`from __feature__ import snake_case`](https://doc.qt.io/qtforpython/feature-why.html).
This will allow us to write code like `QMainWindow.set_window_title()`
instead of `QMainWindow.setWindowTitle()`.  To get a module set up the 
`__feature__` import must occur after the first `PySide6` import, for
example:

```python
from PySide6.QtWidgets import QMainWindow

from __feature__ import snake_case  # noqa
```

Note the `# noqa`, this is needed to prevent linters and code inspection
from complaining about the import order.

When this is first implement your linters and code inspection will
likely complain with unresolved instances.  This is because the
[Python stub files](https://peps.python.org/pep-0484/#stub-files)
(i.e. ``.pyi`` files) were generated without this feature enabled.  To
update your stub files follow the procedure below:

1. Determine where `PySide6` is installed.  This can be done by 
   executing `python -m pip show pyside6` in the command prompt.  This
   show be the `site-packages` directory for you Python distribution.
2. Navigate to the directory indicated by step 1.
3. Navigate into the `PySide6/` directory.
4. Now execute the following command in your command prompt:

   ```bash
   pyside6-genpyi all --feature snake_case
   ```
   
   This will update all the stub files accordingly, and should only take
   a few seconds.
