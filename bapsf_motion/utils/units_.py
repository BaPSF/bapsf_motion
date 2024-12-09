"""Functionality for configuring `astropy.units` for `bapsf_motion`."""
__all__ = ["units", "counts", "steps", "rev"]
from astropy import units

# enable imperial units
units.imperial.enable()

#: Base unit for (stepper motor) encoders.
counts = units.def_unit(
    "counts",
    namespace=units.__dict__,
    doc="Base unit for (stepper motor) encoders.",
)

#: Base unit for stepper motors.
steps = units.def_unit(
    "steps",
    namespace=units.__dict__,
    doc="Base unit for stepper motors.",
)

#: A unit for the instance of revolving.
rev = units.def_unit(
    "rev",
    namespace=units.__dict__,
    doc="A unit for the instance of revolving.",
)

for _u in {counts, steps, rev}:
    units.add_enabled_units(_u)
