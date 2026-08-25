"""
Predictive Carbon Estimation Module.
"""

from .api import (
    APIRequestError,
    AuthenticationError,
    ElectricityMapsAPIError,
    ElectricityMapsClient,
    InvalidZoneError,
)
from .converter import EnergyUnitConverter
from .engine import CarbonEstimationEngine
from .estimator import CarbonEstimator
from .models import (
    CarbonEstimate,
    CarbonIntensityData,
    CarbonResult,
    ZoneData,
)
from .providers import (
    CarbonIntensityProvider,
    ElectricityMapsProvider,
    MockCarbonIntensityProvider,
    get_carbon_provider,
)

__all__ = [
    "APIRequestError",
    "AuthenticationError",
    "ElectricityMapsAPIError",
    "ElectricityMapsClient",
    "InvalidZoneError",
    "ZoneData",
    "CarbonIntensityData",
    "CarbonEstimate",
    "CarbonResult",
    "EnergyUnitConverter",
    "CarbonEstimator",
    "CarbonEstimationEngine",
    "CarbonIntensityProvider",
    "ElectricityMapsProvider",
    "MockCarbonIntensityProvider",
    "get_carbon_provider",
]