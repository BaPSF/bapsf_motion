"""Functionality for configuring `astropy.units` for `bapsf_motion`."""
__all__ = ["units", "counts", "steps", "rev"]
from astropy import units

# enable imperial units
units.imperial.enable()

#: Base unit for encoders.
counts = units.def_unit("counts", namespace=units.__dict__)

#: Base unit for stepper motors.
steps = units.def_unit("steps", namespace=units.__dict__)

#: An unit for the instance of revolving.
rev = units.def_unit("rev", namespace=units.__dict__)

for _u in {counts, steps, rev}:
    units.add_enabled_units(_u)
