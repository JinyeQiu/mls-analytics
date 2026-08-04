"""Week 7: detect and handle outliers in the engineered Residential Sold data.

Input (created in Week 6):
    processed/sold_residential_week6_engineered.csv

Main outputs:
    processed/sold_residential_week7_flagged.csv
    processed/sold_residential_week7_filtered.csv

Supporting outputs:
    processed/week7_iqr_thresholds.csv
    processed/week7_before_after_comparison.csv
    processed/week7_before_after_comparison.txt

The standard 1.5 * IQR rule is applied independently to ClosePrice,
LivingArea, and DaysOnMarket. The full flagged output preserves every input
record. The filtered output excludes IQR outliers and records that violate the
defined business rules so it can be used for typical-market analysis.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from pandas.api.types import is_bool_dtype


OUTLIER_FIELDS = {
    "ClosePrice": "close_price_iqr_outlier_flag",
    "LivingArea": "living_area_iqr_outlier_flag",
    "DaysOnMarket": "days_on_market_iqr_outlier_flag",
}

SOURCE_BUSINESS_RULE_FLAGS = [
    "invalid_close_price_flag",
    "invalid_living_area_flag",
    "invalid_days_on_market_flag",
]

WEEK7_FLAG_COLUMNS = [
    *OUTLIER_FIELDS.values(),
    "any_iqr_outlier_flag",
    "week7_business_rule_invalid_flag",
    "week7_exclusion_flag",
]

EXPECTED_INPUT_ROWS = 430_428


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "py" else script_dir
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Flag Week 7 Sold-data outliers and create a filtered copy."
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week6_engineered.csv",
        help="Path to the Week 6 engineered Residential Sold CSV.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=processed_dir,
        help="Directory for the Week 7 datasets and reports.",
    )
    return parser.parse_args()


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [field for field in OUTLIER_FIELDS if field not in df.columns]
    if missing:
        raise KeyError(f"Required Week 7 columns are missing: {missing}")


def normalize_boolean_flag(values: pd.Series, flag_name: str) -> pd.Series:
    """Convert a saved Boolean flag safely instead of treating text as truthy."""
    if is_bool_dtype(values.dtype):
        return values.fillna(False).astype(bool)

    normalized = values.astype("string").str.strip().str.lower()
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
    }
    unexpected = normalized[normalized.notna() & ~normalized.isin(mapping)]
    if not unexpected.empty:
        examples = sorted(unexpected.unique().tolist())[:5]
        raise ValueError(
            f"{flag_name} contains unexpected Boolean values: {examples}"
        )
    return normalized.map(mapping).fillna(False).astype(bool)


def prepare_numeric_fields(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for field in OUTLIER_FIELDS:
        prepared[field] = pd.to_numeric(prepared[field], errors="coerce")
    return prepared


def calculate_iqr_flags(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add record-level IQR flags and return a threshold summary."""
    flagged = prepare_numeric_fields(df)
    summary_rows: list[dict[str, object]] = []

    for field, flag_name in OUTLIER_FIELDS.items():
        values = flagged[field]
        usable = values.dropna()
        if usable.empty:
            raise ValueError(
                f"{field} has no usable numeric values for IQR calculation."
            )

        q1 = usable.quantile(0.25)
        median = usable.median()
        q3 = usable.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        below_lower = values.notna() & (values < lower_bound)
        above_upper = values.notna() & (values > upper_bound)
        outlier = (below_lower | above_upper).astype(bool)
        flagged[flag_name] = outlier

        outlier_count = int(outlier.sum())
        summary_rows.append(
            {
                "field": field,
                "non_missing_count": int(usable.size),
                "missing_count": int(values.isna().sum()),
                "q1": q1,
                "median": median,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "p01": usable.quantile(0.01),
                "p05": usable.quantile(0.05),
                "p95": usable.quantile(0.95),
                "p99": usable.quantile(0.99),
                "below_lower_bound": int(below_lower.sum()),
                "above_upper_bound": int(above_upper.sum()),
                "total_iqr_outliers": outlier_count,
                "iqr_outlier_percent_of_non_missing": (
                    outlier_count / usable.size * 100
                ),
            }
        )

    individual_flags = list(OUTLIER_FIELDS.values())
    flagged["any_iqr_outlier_flag"] = flagged[individual_flags].any(axis=1)
    return flagged, pd.DataFrame(summary_rows).round(4)


def add_business_rule_flags(df: pd.DataFrame) -> pd.DataFrame:
    flagged = df.copy()

    prior_invalid = pd.Series(False, index=flagged.index, dtype=bool)
    for flag_name in SOURCE_BUSINESS_RULE_FLAGS:
        if flag_name in flagged.columns:
            prior_invalid |= normalize_boolean_flag(
                flagged[flag_name], flag_name
            )

    current_invalid = (
        (flagged["ClosePrice"].notna() & (flagged["ClosePrice"] <= 0))
        | (flagged["LivingArea"].notna() & (flagged["LivingArea"] <= 0))
        | (
            flagged["DaysOnMarket"].notna()
            & (flagged["DaysOnMarket"] < 0)
        )
    )

    flagged["week7_business_rule_invalid_flag"] = (
        prior_invalid | current_invalid
    ).astype(bool)
    flagged["week7_exclusion_flag"] = (
        flagged["any_iqr_outlier_flag"]
        | flagged["week7_business_rule_invalid_flag"]
    ).astype(bool)
    return flagged


def median_or_missing(df: pd.DataFrame, field: str) -> float | None:
    median = pd.to_numeric(df[field], errors="coerce").median()
    return None if pd.isna(median) else float(median)


def create_before_after_comparison(
    flagged: pd.DataFrame, filtered: pd.DataFrame
) -> pd.DataFrame:
    removed = len(flagged) - len(filtered)
    percent_removed = removed / len(flagged) * 100 if len(flagged) else 0

    return pd.DataFrame(
        [
            {
                "dataset": "full_flagged",
                "row_count": len(flagged),
                "rows_removed_from_full": 0,
                "percent_removed_from_full": 0.0,
                "median_close_price": median_or_missing(
                    flagged, "ClosePrice"
                ),
                "median_living_area": median_or_missing(
                    flagged, "LivingArea"
                ),
                "median_days_on_market": median_or_missing(
                    flagged, "DaysOnMarket"
                ),
            },
            {
                "dataset": "filtered_analysis",
                "row_count": len(filtered),
                "rows_removed_from_full": removed,
                "percent_removed_from_full": percent_removed,
                "median_close_price": median_or_missing(
                    filtered, "ClosePrice"
                ),
                "median_living_area": median_or_missing(
                    filtered, "LivingArea"
                ),
                "median_days_on_market": median_or_missing(
                    filtered, "DaysOnMarket"
                ),
            },
        ]
    ).round(2)


def format_number(value: object, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "not available"
    return f"{float(value):,.{decimals}f}"


def create_written_comparison(
    flagged: pd.DataFrame, filtered: pd.DataFrame
) -> str:
    removed = len(flagged) - len(filtered)
    percent_removed = removed / len(flagged) * 100 if len(flagged) else 0

    return (
        "Week 7 Before-and-After Comparison\n"
        "==================================\n\n"
        f"The full flagged dataset contained {len(flagged):,} records. "
        f"After excluding records flagged by the IQR method or the defined "
        f"business rules, the filtered dataset contained {len(filtered):,} "
        f"records. This removed {removed:,} records ({percent_removed:.2f}%).\n\n"
        "Median ClosePrice changed from "
        f"${format_number(median_or_missing(flagged, 'ClosePrice'), 2)} to "
        f"${format_number(median_or_missing(filtered, 'ClosePrice'), 2)}. "
        "Median LivingArea changed from "
        f"{format_number(median_or_missing(flagged, 'LivingArea'))} to "
        f"{format_number(median_or_missing(filtered, 'LivingArea'))} square "
        "feet. Median DaysOnMarket changed from "
        f"{format_number(median_or_missing(flagged, 'DaysOnMarket'), 1)} to "
        f"{format_number(median_or_missing(filtered, 'DaysOnMarket'), 1)} "
        "days.\n\n"
        "The full flagged dataset preserves all transactions for auditing. "
        "The filtered dataset is intended for typical-market analysis; an IQR "
        "outlier is not automatically an incorrect transaction.\n"
    )


def validate_outputs(
    original: pd.DataFrame,
    flagged: pd.DataFrame,
    filtered: pd.DataFrame,
) -> None:
    if len(original) != EXPECTED_INPUT_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_INPUT_ROWS:,} Week 6 rows, but loaded "
            f"{len(original):,}. Confirm that the correct input file is being "
            "used."
        )

    if len(flagged) != len(original):
        raise ValueError("The full flagged dataset changed the input row count.")

    missing_original_columns = [
        column for column in original.columns if column not in flagged.columns
    ]
    if missing_original_columns:
        raise ValueError(
            "The flagged dataset lost original Week 6 columns: "
            f"{missing_original_columns}"
        )

    non_boolean = [
        flag for flag in WEEK7_FLAG_COLUMNS if not is_bool_dtype(flagged[flag])
    ]
    if non_boolean:
        raise TypeError(f"Week 7 flags are not Boolean: {non_boolean}")

    expected_any = flagged[list(OUTLIER_FIELDS.values())].any(axis=1)
    if not flagged["any_iqr_outlier_flag"].equals(expected_any):
        raise ValueError("any_iqr_outlier_flag does not combine its field flags.")

    expected_exclusion = (
        flagged["any_iqr_outlier_flag"]
        | flagged["week7_business_rule_invalid_flag"]
    )
    if not flagged["week7_exclusion_flag"].equals(expected_exclusion):
        raise ValueError("week7_exclusion_flag does not combine its source flags.")

    if filtered.empty:
        raise ValueError("The filtered Week 7 dataset is unexpectedly empty.")

    if filtered["week7_exclusion_flag"].any():
        raise ValueError("Excluded records remain in the filtered dataset.")

    excluded_count = int(flagged["week7_exclusion_flag"].sum())
    if len(filtered) != len(flagged) - excluded_count:
        raise ValueError("The before-and-after Week 7 row counts do not reconcile.")


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    if not args.sold.exists():
        raise FileNotFoundError(f"Input file not found: {args.sold}")

    print(f"Loading {args.sold}...")
    sold = pd.read_csv(args.sold, low_memory=False)
    print(f"Loaded {len(sold):,} rows and {len(sold.columns)} columns.")
    validate_required_columns(sold)

    flagged, thresholds = calculate_iqr_flags(sold)
    flagged = add_business_rule_flags(flagged)
    filtered = flagged.loc[~flagged["week7_exclusion_flag"]].copy()
    comparison = create_before_after_comparison(flagged, filtered)
    written_comparison = create_written_comparison(flagged, filtered)

    validate_outputs(sold, flagged, filtered)

    flagged_output = args.outdir / "sold_residential_week7_flagged.csv"
    filtered_output = args.outdir / "sold_residential_week7_filtered.csv"
    thresholds_output = args.outdir / "week7_iqr_thresholds.csv"
    comparison_output = args.outdir / "week7_before_after_comparison.csv"
    comparison_text_output = (
        args.outdir / "week7_before_after_comparison.txt"
    )

    flagged.to_csv(flagged_output, index=False)
    filtered.to_csv(filtered_output, index=False)
    thresholds.to_csv(thresholds_output, index=False)
    comparison.to_csv(comparison_output, index=False)
    comparison_text_output.write_text(written_comparison, encoding="utf-8")

    print("\nIQR thresholds and outlier counts:")
    print(thresholds.to_string(index=False))
    print("\nBefore-and-after comparison:")
    print(comparison.to_string(index=False))

    print("\nWeek 7 outlier detection completed successfully.")
    print(f"Rows in full flagged dataset: {len(flagged):,}")
    print(f"Rows in filtered dataset:     {len(filtered):,}")
    print(f"Rows excluded:                {len(flagged) - len(filtered):,}")
    print(f"Saved {flagged_output}")
    print(f"Saved {filtered_output}")
    print(f"Saved {thresholds_output}")
    print(f"Saved {comparison_output}")
    print(f"Saved {comparison_text_output}")


if __name__ == "__main__":
    main()
