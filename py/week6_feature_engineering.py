"""Week 6: engineer market metrics from the cleaned Residential Sold dataset.

Input (created in Weeks 4-5):
    processed/sold_residential_week4_5_clean.csv

Main output:
    processed/sold_residential_week6_engineered.csv

Validation and demonstration outputs:
    processed/week6_sample_output.csv
    processed/week6_feature_summary.csv
    processed/week6_segment_property_type.csv
    processed/week6_segment_property_subtype.csv
    processed/week6_segment_county.csv
    processed/week6_segment_mls_area_major.csv
    processed/week6_segment_list_office.csv
    processed/week6_segment_buyer_office.csv

The script preserves every input row. Ratios are calculated only when their
denominators are positive. Negative date intervals are flagged and replaced
with missing values so invalid timelines do not distort later analysis.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "ClosePrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
]

NUMERIC_SOURCE_FIELDS = [
    "ClosePrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
]

DATE_SOURCE_FIELDS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
]

ENGINEERED_METRICS = [
    "PriceRatio",
    "CloseToOriginalListRatio",
    "PricePerSqFt",
    "DaysOnMarket",
    "Year",
    "Month",
    "YrMo",
    "ListingToContractDays",
    "ContractToCloseDays",
]

SEGMENTS = {
    "PropertyType": "property_type",
    "PropertySubType": "property_subtype",
    "CountyOrParish": "county",
    "MLSAreaMajor": "mls_area_major",
    "ListOfficeName": "list_office",
    "BuyerOfficeName": "buyer_office",
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "py" else script_dir
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Create Week 6 housing-market features and segment summaries."
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week4_5_clean.csv",
        help="Path to the cleaned Weeks 4-5 Sold CSV.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=processed_dir,
        help="Directory for the engineered dataset and summary outputs.",
    )
    return parser.parse_args()


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise KeyError(f"Required Week 6 columns are missing: {missing}")


def prepare_source_types(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    for field in NUMERIC_SOURCE_FIELDS:
        prepared[field] = pd.to_numeric(prepared[field], errors="coerce")

    for field in DATE_SOURCE_FIELDS:
        prepared[field] = pd.to_datetime(prepared[field], errors="coerce")

    return prepared


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    engineered = prepare_source_types(df)

    valid_original_price = (
        engineered["ClosePrice"].notna()
        & engineered["OriginalListPrice"].notna()
        & (engineered["OriginalListPrice"] > 0)
    )
    close_to_original = pd.Series(np.nan, index=engineered.index, dtype="float64")
    close_to_original.loc[valid_original_price] = (
        engineered.loc[valid_original_price, "ClosePrice"]
        / engineered.loc[valid_original_price, "OriginalListPrice"]
    )

    # The handbook defines both names with the same formula. Keep both columns
    # so the deliverable explicitly demonstrates each requested metric.
    engineered["PriceRatio"] = close_to_original
    engineered["CloseToOriginalListRatio"] = close_to_original

    valid_living_area = (
        engineered["ClosePrice"].notna()
        & engineered["LivingArea"].notna()
        & (engineered["LivingArea"] > 0)
    )
    engineered["PricePerSqFt"] = np.nan
    engineered.loc[valid_living_area, "PricePerSqFt"] = (
        engineered.loc[valid_living_area, "ClosePrice"]
        / engineered.loc[valid_living_area, "LivingArea"]
    )

    engineered["Year"] = engineered["CloseDate"].dt.year.astype("Int64")
    engineered["Month"] = engineered["CloseDate"].dt.month.astype("Int64")
    engineered["YrMo"] = engineered["CloseDate"].dt.strftime("%Y-%m")

    listing_to_contract = (
        engineered["PurchaseContractDate"] - engineered["ListingContractDate"]
    ).dt.days
    contract_to_close = (
        engineered["CloseDate"] - engineered["PurchaseContractDate"]
    ).dt.days

    engineered["invalid_listing_to_contract_days_flag"] = (
        listing_to_contract < 0
    ).fillna(False)
    engineered["invalid_contract_to_close_days_flag"] = (
        contract_to_close < 0
    ).fillna(False)

    engineered["ListingToContractDays"] = listing_to_contract.mask(
        engineered["invalid_listing_to_contract_days_flag"]
    ).astype("Int64")
    engineered["ContractToCloseDays"] = contract_to_close.mask(
        engineered["invalid_contract_to_close_days_flag"]
    ).astype("Int64")

    return engineered


def create_feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for metric in ENGINEERED_METRICS:
        values = df[metric]
        numeric = pd.to_numeric(values, errors="coerce")
        populated = int(values.notna().sum())
        has_numeric_values = numeric.notna().any()
        rows.append(
            {
                "metric": metric,
                "populated_rows": populated,
                "missing_rows": int(values.isna().sum()),
                "populated_percent": round(populated / len(df) * 100, 2)
                if len(df)
                else 0,
                "minimum": numeric.min() if has_numeric_values else None,
                "median": numeric.median() if has_numeric_values else None,
                "mean": numeric.mean() if has_numeric_values else None,
                "maximum": numeric.max() if has_numeric_values else None,
            }
        )

    return pd.DataFrame(rows).round(2)


def create_segment_summary(
    df: pd.DataFrame, segment_field: str
) -> pd.DataFrame:
    usable = df[df[segment_field].notna()].copy()

    summary = (
        usable.groupby(segment_field, dropna=False)
        .agg(
            record_count=("ClosePrice", "size"),
            closed_sales_count=("ClosePrice", "count"),
            total_sales_volume=("ClosePrice", "sum"),
            average_close_price=("ClosePrice", "mean"),
            median_close_price=("ClosePrice", "median"),
            average_price_per_sq_ft=("PricePerSqFt", "mean"),
            median_price_per_sq_ft=("PricePerSqFt", "median"),
            average_days_on_market=("DaysOnMarket", "mean"),
            median_days_on_market=("DaysOnMarket", "median"),
            average_close_to_original_list_ratio=(
                "CloseToOriginalListRatio",
                "mean",
            ),
            median_close_to_original_list_ratio=(
                "CloseToOriginalListRatio",
                "median",
            ),
            median_listing_to_contract_days=("ListingToContractDays", "median"),
            median_contract_to_close_days=("ContractToCloseDays", "median"),
        )
        .reset_index()
        .sort_values(
            ["closed_sales_count", "total_sales_volume"],
            ascending=[False, False],
        )
    )

    return summary.round(2)


def create_sample_output(df: pd.DataFrame, sample_size: int = 10) -> pd.DataFrame:
    identifiers = [
        column
        for column in [
            "ListingKey",
            "UnparsedAddress",
            "CountyOrParish",
            "PropertySubType",
            "CloseDate",
            "OriginalListPrice",
            "ClosePrice",
            "LivingArea",
            "PurchaseContractDate",
            "ListingContractDate",
        ]
        if column in df.columns
    ]
    sample_columns = identifiers + [
        metric for metric in ENGINEERED_METRICS if metric not in identifiers
    ]

    sample = df.dropna(subset=ENGINEERED_METRICS).head(sample_size)
    if sample.empty:
        raise ValueError(
            "No rows have all Week 6 metrics populated. Review the source dates "
            "and numeric fields before creating the required sample table."
        )

    return sample[sample_columns]


def validate_engineered_dataset(
    original: pd.DataFrame, engineered: pd.DataFrame
) -> None:
    if len(engineered) != len(original):
        raise ValueError("Week 6 feature engineering changed the row count.")

    if not engineered["PriceRatio"].equals(
        engineered["CloseToOriginalListRatio"]
    ):
        raise ValueError("The two handbook-defined original-list ratios disagree.")

    if (engineered["ListingToContractDays"].dropna() < 0).any():
        raise ValueError("Negative ListingToContractDays values remain.")

    if (engineered["ContractToCloseDays"].dropna() < 0).any():
        raise ValueError("Negative ContractToCloseDays values remain.")

    finite_ratio = engineered["PriceRatio"].dropna()
    finite_ppsf = engineered["PricePerSqFt"].dropna()
    if not np.isfinite(finite_ratio).all() or not np.isfinite(finite_ppsf).all():
        raise ValueError("An engineered ratio contains an infinite value.")

    invalid_yrmo = engineered["YrMo"].dropna().str.fullmatch(r"\d{4}-\d{2}")
    if not invalid_yrmo.all():
        raise ValueError("One or more YrMo values do not follow YYYY-MM format.")


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    if not args.sold.exists():
        raise FileNotFoundError(f"Input file not found: {args.sold}")

    print(f"Loading {args.sold}...")
    sold = pd.read_csv(args.sold, low_memory=False)
    print(f"Loaded {len(sold):,} rows and {len(sold.columns)} columns.")
    validate_required_columns(sold)

    engineered = engineer_features(sold)
    validate_engineered_dataset(sold, engineered)

    engineered_output = (
        args.outdir / "sold_residential_week6_engineered.csv"
    )
    sample_output = args.outdir / "week6_sample_output.csv"
    feature_summary_output = args.outdir / "week6_feature_summary.csv"

    engineered.to_csv(engineered_output, index=False, date_format="%Y-%m-%d")

    sample = create_sample_output(engineered)
    sample.to_csv(sample_output, index=False, date_format="%Y-%m-%d")

    feature_summary = create_feature_summary(engineered)
    feature_summary.to_csv(feature_summary_output, index=False)

    segment_outputs: list[tuple[str, Path, int]] = []
    for field, output_suffix in SEGMENTS.items():
        if field not in engineered.columns:
            print(f"Segment skipped because {field} is not available.")
            continue
        segment_summary = create_segment_summary(engineered, field)
        output_path = args.outdir / f"week6_segment_{output_suffix}.csv"
        segment_summary.to_csv(output_path, index=False)
        segment_outputs.append((field, output_path, len(segment_summary)))

    if not segment_outputs:
        raise ValueError("None of the requested segment fields are available.")

    print("\nSample of populated Week 6 metrics:")
    print(sample.to_string(index=False))
    print("\nFeature population summary:")
    print(feature_summary.to_string(index=False))
    print("\nSegment summaries:")
    for field, output_path, group_count in segment_outputs:
        print(f"  {field}: {group_count:,} groups -> {output_path}")

    print("\nWeek 6 feature engineering completed successfully.")
    print(f"Rows before: {len(sold):,}")
    print(f"Rows after:  {len(engineered):,}")
    print(f"Saved {engineered_output}")
    print(f"Saved {sample_output}")
    print(f"Saved {feature_summary_output}")


if __name__ == "__main__":
    main()
