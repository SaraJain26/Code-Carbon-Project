"""
Command-line interface for predictive carbon estimation.
"""

from __future__ import annotations

import argparse
import sys
from typing import cast

from energy.models import EnergyResult
from pipeline import PredictivePipeline

from .api import (
    APIRequestError,
    AuthenticationError,
    InvalidZoneError,
)
from .providers import get_carbon_provider
from .models import CarbonResult


def create_pipeline() -> PredictivePipeline:
    """
    Create a PredictivePipeline instance.
    """

    return PredictivePipeline()


def _run_pipeline(
    source: str,
    *,
    zone: str,
    use_global_average: bool = False,
) -> tuple[PredictivePipeline, dict[str, object]]:

    pipeline = create_pipeline()

    result = pipeline.run(
        source,
        zone=zone,
        use_global_average=use_global_average,
    )

    return pipeline, result


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line parser.
    """

    parser = argparse.ArgumentParser(
        prog="codecarbon",
        description=(
            "Predictive carbon estimation using "
            "Electricity Maps."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    estimate = subparsers.add_parser(
        "estimate",
        help="Estimate software carbon emissions.",
    )

    estimate.add_argument(
        "source",
        help="Path to the Python source file.",
    )

    estimate.add_argument(
        "--zone",
        required=True,
        help="Electricity Maps zone identifier.",
    )

    estimate.add_argument(
        "--global-average",
        action="store_true",
        help=(
            "Fallback to the default global "
            "carbon intensity if the API fails."
        ),
    )

    forecast = subparsers.add_parser(
        "forecast",
        help="Estimate emissions using forecast data.",
    )

    forecast.add_argument(
        "source",
        help="Path to the Python source file.",
    )

    forecast.add_argument(
        "--zone",
        required=True,
        help="Electricity Maps zone identifier.",
    )

    subparsers.add_parser(
        "zones",
        help="List all supported Electricity Maps zones.",
    )

    search = subparsers.add_parser(
        "search-zones",
        help="Search Electricity Maps zones.",
    )

    search.add_argument(
        "query",
        help="Search query.",
    )

    return parser


def command_estimate(
    args: argparse.Namespace,
) -> int:

    try:

        _pipeline, result = _run_pipeline(
            args.source,
            zone=args.zone,
            use_global_average=args.global_average,
        )

        carbon_result = cast(
            CarbonResult,
            result["carbon_result"],
        )

        energy_result = cast(
            EnergyResult,
            result["energy_result"],
        )

        print()

        print("=" * 60)
        print("Carbon Estimation")
        print("=" * 60)

        print(
            f"Zone                  : "
            f"{carbon_result.carbon_data.zone.zone_key}"
        )

        print(
            f"Country               : "
            f"{carbon_result.carbon_data.zone.country_name}"
        )

        print(
            f"Carbon Intensity      : "
            f"{carbon_result.carbon_data.carbon_intensity:.2f} "
            f"gCO₂eq/kWh"
        )

        print(
            f"Energy                : "
            f"{energy_result.energy.energy_joules:.6f} J"
        )

        print(
            f"Estimated Carbon      : "
            f"{carbon_result.carbon.carbon_grams:.6f} gCO₂eq"
        )

        print(
            f"Data Source           : "
            f"{carbon_result.carbon_data.source}"
        )

        print(
            f"Fallback Used         : "
            f"{carbon_result.fallback_used}"
        )

        from sustainability.metrics import ResearchSustainabilityMetrics
        smell_report = result["energy_smell_report"]
        complexity_score = result["complexity_score"]
        
        ess = ResearchSustainabilityMetrics.compute_energy_smell_score(smell_report)
        cirs_research = ResearchSustainabilityMetrics.compute_carbon_impact_risk_score(
            complexity=complexity_score,
            energy_result=energy_result,
            carbon_result=carbon_result,
            ess=ess
        )

        print(
            f"Research Smell (ESS)  : "
            f"{ess:.2f}/10"
        )

        print(
            f"Research CIRS         : "
            f"{cirs_research:.6f} e-gCO₂eq"
        )

        print()

        return 0

    except AuthenticationError:

        print(
            "Authentication failed. "
            "Check your Electricity Maps API key.",
            file=sys.stderr,
        )

    except InvalidZoneError:

        print(
            "Invalid Electricity Maps Zone ID.",
            file=sys.stderr,
        )

    except APIRequestError as exc:

        print(
            str(exc),
            file=sys.stderr,
        )

    return 1


def command_forecast(
    args: argparse.Namespace,
) -> int:

    try:

        pipeline, result = _run_pipeline(
            args.source,
            zone=args.zone,
        )

        carbon_result = cast(
            CarbonResult,
            result["carbon_result"],
        )

        energy_result = cast(
            EnergyResult,
            result["energy_result"],
        )

        forecasts = pipeline._carbon_engine.forecast(
            energy_result,
            zone=args.zone,
        )

        best = pipeline._carbon_engine.best_execution_window(
            forecasts,
        )

        reduction = pipeline._carbon_engine.percentage_reduction(
            carbon_result,
            best,
        )

        print()

        print("=" * 60)
        print("Forecast Recommendation")
        print("=" * 60)

        print(
            f"Current Carbon Intensity : "
            f"{carbon_result.carbon_data.carbon_intensity:.2f}"
            f" gCO₂eq/kWh"
        )

        print(
            f"Lowest Forecast          : "
            f"{best.carbon_data.carbon_intensity:.2f}"
            f" gCO₂eq/kWh"
        )

        print(
            f"Expected Reduction       : "
            f"{reduction:.2f}%"
        )

        print(
            f"Recommended Execution    : "
            f"{best.carbon_data.timestamp}"
        )

        print()

        return 0

    except (
        AuthenticationError,
        InvalidZoneError,
        APIRequestError,
    ) as exc:

        print(
            str(exc),
            file=sys.stderr,
        )

        return 1


def command_zones() -> int:

    try:

        client = get_carbon_provider()

        zones = client.get_all_zones()

        print()

        print("=" * 80)
        print("Supported Electricity Maps Zones")
        print("=" * 80)

        for zone in sorted(
            zones.values(),
            key=lambda item: item.zone_key,
        ):

            print(
                f"{zone.zone_key:<18}"
                f"{zone.country_name:<25}"
                f"{zone.display_name}"
            )

        print()

        return 0

    except (
        AuthenticationError,
        APIRequestError,
    ) as exc:

        print(
            str(exc),
            file=sys.stderr,
        )

        return 1


def command_search_zones(
    args: argparse.Namespace,
) -> int:

    try:

        client = get_carbon_provider()

        matches = client.search_zones(
            args.query,
        )

        if not matches:

            print(
                "No matching zones found.",
            )

            return 0

        print()

        print("=" * 80)
        print(
            f"Search Results for '{args.query}'"
        )
        print("=" * 80)

        for zone in sorted(
            matches.values(),
            key=lambda item: item.zone_key,
        ):

            print(
                f"{zone.zone_key:<18}"
                f"{zone.country_name:<25}"
                f"{zone.display_name}"
            )

        print()

        return 0

    except (
        AuthenticationError,
        APIRequestError,
    ) as exc:

        print(
            str(exc),
            file=sys.stderr,
        )

        return 1


def main() -> int:

    parser = build_parser()

    args = parser.parse_args()

    if args.command == "estimate":

        return command_estimate(
            args,
        )

    if args.command == "forecast":

        return command_forecast(
            args,
        )

    if args.command == "zones":

        return command_zones()

    if args.command == "search-zones":

        return command_search_zones(
            args,
        )

    parser.print_help()

    return 1


if __name__ == "__main__":

    raise SystemExit(
        main(),
    )