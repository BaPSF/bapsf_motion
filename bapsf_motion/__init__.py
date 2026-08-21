"""`bapsf_motion`"""

__all__ = ["__version__"]

# Enforce Python version check during package import.
# This is the same check as the one at the top of setup.py
import sys

if sys.version_info < (3, 10):  # coverage: ignore
    raise ImportError("bapsf_motion does not support Python < 3.10")

from importlib.metadata import PackageNotFoundError, version

from bapsf_motion import actors, motion_builder, transform, utils

# define version
try:
    # this places a runtime dependency on setuptools
    #
    # note: if there's any distribution metadata in your source files, then this
    #       will find a version based on those files.  Keep distribution metadata
    #       out of your repository unless you've intentionally installed the package
    #       as editable (e.g. `pip install -e {bapsf_motion_directory_root}`),
    #       but then __version__ will not be updated with each commit, it is
    #       frozen to the version at time of install.
    #
    #: bapsf_motion version string
    __version__ = version("bapsf_motion")
except PackageNotFoundError:
    # package is not installed
    fallback_version = "unknown"
    try:
        # code most likely being used from source
        # if setuptools_scm is installed then generate a version
        #
        # Notes:
        #  - setuptools_scm.get_version does not read configuration parameters
        #    from the pyproject.toml and does NOT allows us to pass those
        #    configuration parameters at call ... this is the case as of 20260820
        #  - this means the FutureWarning for not explicitly defining
        #    tools.setuptools_scm.tag.strict is unavoidable (at the moment)
        #  - I [Erik] discovered a bit of a workaround, but it is not pretty
        #    and I do not think it is necessary here.  Because, (1) this
        #    block is only reached when bapsf_motion is NOT installed
        #    and (2) setuptools_scm will eventually default to tag.strict = true
        #    which is what is set in the pyproject.toml.  For completeness,
        #    I am leaving the "ugly" code here:
        #
        #    from pathlib import Path
        #    from setuptools_scm import _get_version
        #    from vcs_versioning import PyProjectData, build_configuration_from_pyproject
        #    from vcs_versioning.overrides import GlobalOverrides
        #
        #    _path = (Path(__file__).parent / ".." / "pyproject.toml").resolve()
        #    with GlobalOverrides.from_env("SETUPTOOLS_SCM", dist_name="bapsf_motion"):
        #        pyproject_data = PyProjectData.from_file(
        #            _path,
        #            _tool_names=["setuptools_scm", "vcs-versioning"],
        #        )
        #        config = build_configuration_from_pyproject(
        #            pyproject_data=pyproject_data,
        #            dist_name="bapsf_motion",
        #            fallback_version=fallback_version,
        #        )
        #
        #    __version__ = _get_version(config, force_write_version_files=True)
        #
        #  - I am going to leave the code as is and let the FuturWarning
        #    remain.

        from setuptools_scm import get_version

        __version__ = get_version(
            root="../", relative_to=__file__, fallback_version=fallback_version
        )
        del get_version
        warn_add = "setuptools_scm failed to detect the version"
    except ModuleNotFoundError:
        # setuptools_scm is not installed
        __version__ = fallback_version
        warn_add = "setuptools_scm is not installed"

    if __version__ == fallback_version:
        from warnings import warn

        warn(
            f"bapsf_motion.__version__ not generated (set to 'unknown'), "
            f"bapsf_motion is not an installed package and {warn_add}.",
            RuntimeWarning,
        )

        del warn
    del fallback_version, warn_add
