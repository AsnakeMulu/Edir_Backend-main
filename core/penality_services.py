from decimal import Decimal, ROUND_HALF_UP
from math import floor

from api.models import PenaltyConfiguration


def calculate_penalty(
    penalty_config,
    fee_amount,
    due_date,
    calculation_date=None,
    outstanding_amount=None,
):
    """
    Calculate penalty for a fee.

    Returns:
        {
            "penalty": Decimal,
            "days_late": int,
            "penalty_days": int,
            "increment_count": int,
        }
    """

    if not penalty_config:
        return {
            "penalty": Decimal("0.00"),
            "days_late": 0,
            "penalty_days": 0,
            "increment_count": 0,
        }

    if not penalty_config.enabled:
        return {
            "penalty": Decimal("0.00"),
            "days_late": 0,
            "penalty_days": 0,
            "increment_count": 0,
        }

    # -----------------------------
    # Determine calculation date
    # -----------------------------

    if calculation_date is None:
        from django.utils import timezone
        calculation_date = timezone.localdate()

    # Make sure due_date is a date
    if hasattr(due_date, "date"):
        due_date = due_date.date()

    # -----------------------------
    # Calculate days late
    # -----------------------------

    days_late = (calculation_date - due_date).days

    if days_late <= 0:
        return {
            "penalty": Decimal("0.00"),
            "days_late": 0,
            "penalty_days": 0,
            "increment_count": 0,
        }

    # -----------------------------
    # Tolerance period
    # -----------------------------

    if days_late <= penalty_config.tolerance_days:
        return {
            "penalty": Decimal("0.00"),
            "days_late": days_late,
            "penalty_days": 0,
            "increment_count": 0,
        }

    # Days actually subject to penalty
    penalty_days = (days_late - penalty_config.tolerance_days)

    # -----------------------------
    # Initial penalty
    # -----------------------------

    if penalty_config.calculation_type == (PenaltyConfiguration.FLAT):
        penalty = Decimal(str(penalty_config.initial_value))
    else:
        if penalty_config.percentage_base == (
            PenaltyConfiguration.PERCENTAGE
        ):
            base_amount = (
                outstanding_amount
                if outstanding_amount is not None
                else fee_amount
            )
        else:
            base_amount = fee_amount

        base_amount = Decimal(str(base_amount))

        penalty = (
            base_amount
            * Decimal(str(penalty_config.initial_value))
            / Decimal("100")
        )

    # -----------------------------
    # Incremental penalty
    # -----------------------------

    increment_count = 0

    if (
        penalty_config.incremental
        and penalty_config.increment_interval_days
        and penalty_config.increment_value
    ):

        increment_count = floor(
            (penalty_days - 1)
            / penalty_config.increment_interval_days
        )

        if increment_count > 0:

            if penalty_config.calculation_type == (
                PenaltyConfiguration.FLAT
            ):

                penalty += (
                    Decimal(
                        str(penalty_config.increment_value)
                    )
                    * increment_count
                )

            else:

                if penalty_config.percentage_base == (
                    PenaltyConfiguration.PERCENTAGE
                ):
                    base_amount = (
                        outstanding_amount
                        if outstanding_amount is not None
                        else fee_amount
                    )
                else:
                    base_amount = fee_amount

                base_amount = Decimal(str(base_amount))

                additional_percentage = (
                    Decimal(
                        str(penalty_config.increment_value)
                    )
                    * increment_count
                )

                penalty += (
                    base_amount
                    * additional_percentage
                    / Decimal("100")
                )

    # -----------------------------
    # Maximum penalty
    # -----------------------------

    if penalty_config.maximum_penalty is not None:

        if penalty_config.calculation_type == (
            PenaltyConfiguration.FLAT
        ):

            maximum = Decimal(
                str(penalty_config.maximum_penalty)
            )

        else:

            # For percentage mode, maximum_penalty
            # represents a maximum percentage.
            if penalty_config.percentage_base == (
                PenaltyConfiguration.PERCENTAGE
            ):
                base_amount = (
                    outstanding_amount
                    if outstanding_amount is not None
                    else fee_amount
                )
            else:
                base_amount = fee_amount

            base_amount = Decimal(str(base_amount))

            maximum = (
                base_amount
                * Decimal(
                    str(penalty_config.maximum_penalty)
                )
                / Decimal("100")
            )

        penalty = min(penalty, maximum)

    penalty = penalty.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    return {
        "penalty": penalty,
        "days_late": days_late,
        "penalty_days": penalty_days,
        "increment_count": increment_count,
    }