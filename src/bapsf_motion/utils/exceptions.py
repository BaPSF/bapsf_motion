"""Exceptions and warnings specific to `bapsf_motion`."""
__all__ = [
    "ConfigurationError",
    "ConfigurationWarning",
]


class ConfigurationError(Exception):
    """An exception for incorrect run and motion group configurations."""


class ConfigurationWarning(Warning):
    """A warning for incorrect run and motion group configurations."""
