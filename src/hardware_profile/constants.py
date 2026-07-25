"""
Constants for the Hardware Profiling module.

This file contains:

1. Reference maximum values used for normalization.
2. Reference Compute Power (RCP) values for common processor families.

Normalization limits are design reference values representing
typical upper bounds of modern developer workstations.

Reference Compute Power (RCP) values are representative processor
design power values derived from common Intel and AMD processor
families. These are used only for predictive estimation and are
NOT measured runtime power consumption.
"""

# ==========================================================
# Normalization Reference Values
# ==========================================================

MAX_CPU_CORES = 32
MAX_CPU_FREQUENCY_GHZ = 5.0
MAX_RAM_GB = 64.0

GPU_PRESENT_SCORE = 1.0
GPU_ABSENT_SCORE = 0.0


# ==========================================================
# Intel Reference Compute Power (Watts)
# ==========================================================

INTEL_U_REFERENCE_POWER_W = 15.0
INTEL_P_REFERENCE_POWER_W = 28.0
INTEL_H_REFERENCE_POWER_W = 45.0
INTEL_HX_REFERENCE_POWER_W = 55.0

INTEL_DESKTOP_REFERENCE_POWER_W = 65.0
INTEL_K_REFERENCE_POWER_W = 125.0


# ==========================================================
# AMD Reference Compute Power (Watts)
# ==========================================================

AMD_U_REFERENCE_POWER_W = 15.0
AMD_HS_REFERENCE_POWER_W = 35.0
AMD_H_REFERENCE_POWER_W = 45.0
AMD_HX_REFERENCE_POWER_W = 55.0

AMD_DESKTOP_REFERENCE_POWER_W = 65.0


# ==========================================================
# Apple Silicon
# ==========================================================

# Apple does not officially publish TDP values.
# This value represents a reference compute power estimate.

APPLE_M_REFERENCE_POWER_W = 22.0


# ==========================================================
# Default
# ==========================================================

UNKNOWN_REFERENCE_POWER_W = 45.0