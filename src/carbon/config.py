"""
Configuration for the Carbon Estimation module.

This module centralizes all configurable values used by the
Electricity Maps integration and fallback behaviour.

No mathematical computations should be implemented here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Electricity Maps API
# ---------------------------------------------------------------------

API_BASE_URL = "https://api.electricitymaps.com/v3"

API_KEY_ENVIRONMENT_VARIABLE = "ELECTRICITYMAPS_API_KEY"

API_TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------
# Optional fallback
# ---------------------------------------------------------------------

ENABLE_GLOBAL_FALLBACK = True

DEFAULT_GLOBAL_CARBON_INTENSITY = 435.0

DEFAULT_GLOBAL_CARBON_INTENSITY_SOURCE = (
    "International Energy Agency (IEA), "
    "Electricity 2026 Report "
    "(2025 global average estimate)"
)


# ---------------------------------------------------------------------
# User configuration
# ---------------------------------------------------------------------

DEFAULT_CONFIGURATION_FILE = "config.json"

DEFAULT_ZONE_KEY = "default_zone"