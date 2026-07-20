"""Weeks 4-5: clean and prepare the enriched Residential MLS datasets.

Inputs (created in Week 3):
    processed/listings_residential_week3_enriched.csv
    processed/sold_residential_week3_enriched.csv

Main outputs:
    processed/listings_residential_week4_5_clean.csv
    processed/sold_residential_week4_5_clean.csv

Validation outputs:
    processed/week4_5_dataset_summary.csv
    processed/week4_5_data_type_confirmation.csv
    processed/week4_5_date_consistency_summary.csv
    processed/week4_5_geographic_quality_summary.csv
    processed/week4_5_numeric_quality_summary.csv
    processed/week4_5_redundant_columns_report.csv
    processed/week4_5_transformation_log.txt

Cleaning principles:
* Duplicate ``.1`` columns are coalesced into their base columns before removal.
* Invalid numeric values are flagged and replaced with missing values; entire
  records are not deleted simply because one field is invalid.
* Missing values are preserved when no defensible imputation rule exists.
* Date and geographic problems are flagged rather than silently discarded.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DATE_FIELDS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

NUMERIC_FIELDS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "DaysOnMarket",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

# Approximate California bounding box. This is a broad quality-control screen,
# not a precise state-boundary test.
CA_LATITUDE_MIN = 32.0
CA_LATITUDE_MAX = 42.1
CA_LONGITUDE_MIN = -124.5
CA_LONGITUDE_MAX = -114.0


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "py" else script_dir
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Prepare Week 3 enriched MLS data for analysis."
    )
    parser.add_argument(
        "--listings",
        type=Path,
        default=processed_dir / "listings_residential_week3_enriched.csv",
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week3_enriched.csv",
    )
    parser.add_argument("--outdir", type=Path, default=processed_dir)
    return parser.parse_args()


def values_agree(left: pd.Series, right: pd.Series) -> pd.Series:
    """Compare duplicate columns while tolerating equivalent numeric formats."""
    exact = left.astype("string").eq(right.astype("string")).fillna(False)
    left_number = pd.to_numeric(left, errors="coerce")
    right_number = pd.to_numeric(right, errors="coerce")
    numeric = pd.Series(
        np.isclose(left_number, right_number, equal_nan=False),
        index=left.index,
    )
    return exact | numeric


def coalesce_redundant_columns(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Fill base-column gaps from duplicate .1 columns, then drop duplicates."""
    cleaned = df.copy()
    report_rows: list[dict[str, object]] = []

    duplicate_columns = sorted(
        column
        for column in cleaned.columns
        if column.endswith(".1") and column[:-2] in cleaned.columns
    )

    for duplicate in duplicate_columns:
        base = duplicate[:-2]
        both_present = cleaned[base].notna() & cleaned[duplicate].notna()
        conflicts = both_present & ~values_agree(cleaned[base], cleaned[duplicate])
        filled_from_duplicate = cleaned[base].isna() & cleaned[duplicate].notna()

        cleaned[base] = cleaned[base].combine_first(cleaned[duplicate])
        cleaned = cleaned.drop(columns=duplicate)

        report_rows.append(
            {
                "dataset": dataset_name,
                "base_column": base,
                "removed_duplicate_column": duplicate,
                "values_filled_from_duplicate": int(filled_from_duplicate.sum()),
                "conflicting_non_missing_values": int(conflicts.sum()),
                "conflict_action": "retained base-column value",
            }
        )

    return cleaned, report_rows


def convert_dates(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    rows: list[dict[str, object]] = []

    for field in DATE_FIELDS:
        if field not in cleaned.columns:
            rows.append(
                {
                    "dataset": dataset_name,
                    "column": field,
                    "target_type": "datetime64[ns]",
                    "result_type": "COLUMN NOT AVAILABLE",
                    "non_missing_before": 0,
                    "values_coerced_to_missing": 0,
                }
            )
            continue

        original = cleaned[field]
        converted = pd.to_datetime(original, errors="coerce")
        coerced = original.notna() & converted.isna()
        cleaned[field] = converted
        rows.append(
            {
                "dataset": dataset_name,
                "column": field,
                "target_type": "datetime64[ns]",
                "result_type": str(cleaned[field].dtype),
                "non_missing_before": int(original.notna().sum()),
                "values_coerced_to_missing": int(coerced.sum()),
            }
        )

    return cleaned, rows


def convert_numerics(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    rows: list[dict[str, object]] = []

    for field in NUMERIC_FIELDS:
        if field not in cleaned.columns:
            continue
        original = cleaned[field]
        converted = pd.to_numeric(original, errors="coerce")
        coerced = original.notna() & converted.isna()
        cleaned[field] = converted
        rows.append(
            {
                "dataset": dataset_name,
                "column": field,
                "target_type": "numeric",
                "result_type": str(cleaned[field].dtype),
                "non_missing_before": int(original.notna().sum()),
                "values_coerced_to_missing": int(coerced.sum()),
            }
        )

    return cleaned, rows


def flag_and_null_invalid_numerics(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    rules = {
        "ClosePrice": ("invalid_close_price_flag", lambda s: s <= 0),
        "LivingArea": ("invalid_living_area_flag", lambda s: s <= 0),
        "DaysOnMarket": ("invalid_days_on_market_flag", lambda s: s < 0),
        "BedroomsTotal": ("invalid_bedrooms_flag", lambda s: s < 0),
        "BathroomsTotalInteger": (
            "invalid_bathrooms_flag",
            lambda s: s < 0,
        ),
    }
    rows: list[dict[str, object]] = []

    for field, (flag_name, rule) in rules.items():
        if field not in cleaned.columns:
            continue
        invalid = rule(cleaned[field]).fillna(False)
        cleaned[flag_name] = invalid.astype(bool)
        invalid_count = int(invalid.sum())
        cleaned.loc[invalid, field] = np.nan
        rows.append(
            {
                "dataset": dataset_name,
                "field": field,
                "flag_column": flag_name,
                "invalid_values_found": invalid_count,
                "action": "replaced invalid value with missing; retained row",
            }
        )

    invalid_flags = [
        flag_name for flag_name, _ in rules.values() if flag_name in cleaned.columns
    ]
    cleaned["any_invalid_numeric_flag"] = cleaned[invalid_flags].any(axis=1)
    return cleaned, rows


def add_date_consistency_flags(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()

    def later_than(first: str, second: str) -> pd.Series:
        if first not in cleaned.columns or second not in cleaned.columns:
            return pd.Series(False, index=cleaned.index)
        return (
            cleaned[first].notna()
            & cleaned[second].notna()
            & (cleaned[first] > cleaned[second])
        )

    listing_after_close = later_than("ListingContractDate", "CloseDate")
    purchase_after_close = later_than("PurchaseContractDate", "CloseDate")
    listing_after_purchase = later_than(
        "ListingContractDate", "PurchaseContractDate"
    )

    cleaned["listing_after_close_flag"] = listing_after_close.astype(bool)
    cleaned["purchase_after_close_flag"] = purchase_after_close.astype(bool)
    cleaned["negative_timeline_flag"] = (
        listing_after_close | purchase_after_close | listing_after_purchase
    ).astype(bool)

    rows = []
    for flag in [
        "listing_after_close_flag",
        "purchase_after_close_flag",
        "negative_timeline_flag",
    ]:
        count = int(cleaned[flag].sum())
        rows.append(
            {
                "dataset": dataset_name,
                "flag": flag,
                "flagged_rows": count,
                "flagged_percent": round(count / len(cleaned) * 100, 4)
                if len(cleaned)
                else 0,
            }
        )
    return cleaned, rows


def add_geographic_flags(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    cleaned = df.copy()
    required = {"Latitude", "Longitude"}
    if not required.issubset(cleaned.columns):
        missing_columns = sorted(required.difference(cleaned.columns))
        raise KeyError(
            f"{dataset_name} is missing coordinate columns: {missing_columns}"
        )

    latitude = cleaned["Latitude"]
    longitude = cleaned["Longitude"]
    both_present = latitude.notna() & longitude.notna()

    cleaned["missing_coordinate_flag"] = (~both_present).astype(bool)
    cleaned["zero_coordinate_flag"] = (
        both_present & ((latitude == 0) | (longitude == 0))
    ).astype(bool)
    cleaned["positive_longitude_flag"] = (
        longitude.notna() & (longitude > 0)
    ).astype(bool)
    cleaned["outside_california_bounds_flag"] = (
        both_present
        & ~(
            latitude.between(CA_LATITUDE_MIN, CA_LATITUDE_MAX, inclusive="both")
            & longitude.between(
                CA_LONGITUDE_MIN, CA_LONGITUDE_MAX, inclusive="both"
            )
        )
    ).astype(bool)

    geographic_flags = [
        "missing_coordinate_flag",
        "zero_coordinate_flag",
        "positive_longitude_flag",
        "outside_california_bounds_flag",
    ]
    cleaned["invalid_coordinate_flag"] = cleaned[geographic_flags].any(axis=1)

    # The sold dataset contains Boolean indicators showing that coordinates were
    # filled during an earlier data-preparation process. Preserve and summarize
    # these indicators rather than treating them as coordinate columns.
    fill_indicators = [
        field for field in ["latfilled", "lonfilled"] if field in cleaned.columns
    ]
    if fill_indicators:
        cleaned["coordinate_filled_flag"] = (
            cleaned[fill_indicators].fillna(False).astype(bool).any(axis=1)
        )

    summary_flags = geographic_flags + ["invalid_coordinate_flag"]
    if "coordinate_filled_flag" in cleaned.columns:
        summary_flags.append("coordinate_filled_flag")

    rows = []
    for flag in summary_flags:
        count = int(cleaned[flag].sum())
        rows.append(
            {
                "dataset": dataset_name,
                "flag": flag,
                "flagged_rows": count,
                "flagged_percent": round(count / len(cleaned) * 100, 4)
                if len(cleaned)
                else 0,
            }
        )
    return cleaned, rows


def clean_dataset(
    df: pd.DataFrame, dataset_name: str
) -> tuple[pd.DataFrame, dict[str, list[dict[str, object]]]]:
    before_rows, before_columns = df.shape

    cleaned, redundant_rows = coalesce_redundant_columns(df, dataset_name)
    cleaned, date_type_rows = convert_dates(cleaned, dataset_name)
    cleaned, numeric_type_rows = convert_numerics(cleaned, dataset_name)
    cleaned, numeric_quality_rows = flag_and_null_invalid_numerics(
        cleaned, dataset_name
    )
    cleaned, date_quality_rows = add_date_consistency_flags(cleaned, dataset_name)
    cleaned, geographic_rows = add_geographic_flags(cleaned, dataset_name)

    if len(cleaned) != before_rows:
        raise ValueError(f"{dataset_name}: row count changed unexpectedly.")

    dataset_rows = [
        {
            "dataset": dataset_name,
            "rows_before": before_rows,
            "rows_after": len(cleaned),
            "rows_removed": before_rows - len(cleaned),
            "columns_before": before_columns,
            "columns_after": len(cleaned.columns),
            "redundant_columns_removed": len(redundant_rows),
        }
    ]

    return cleaned, {
        "dataset": dataset_rows,
        "types": date_type_rows + numeric_type_rows,
        "numeric": numeric_quality_rows,
        "dates": date_quality_rows,
        "geographic": geographic_rows,
        "redundant": redundant_rows,
    }


def write_transformation_log(path: Path) -> None:
    text = """Weeks 4-5 Data Cleaning and Preparation
=============================================

1. Input data
   Used the Week 3 Residential datasets enriched with monthly FRED mortgage rates.

2. Redundant columns
   For each Listings column ending in .1 with a matching base column, missing
   base values were filled from the duplicate. The .1 column was then removed.
   When both values were non-missing but disagreed, the base value was retained
   and the conflict was counted in the redundant-column report.

3. Data types
   CloseDate, PurchaseContractDate, ListingContractDate, and
   ContractStatusChangeDate were parsed as datetimes. Required quantitative
   fields were converted to numeric values. Unparseable non-missing values were
   coerced to missing and counted in the type-confirmation report.

4. Missing values
   Missing values were not filled with invented averages or labels. They were
   preserved unless a redundant source column contained the same field. This
   prevents unsupported imputation from distorting later market analysis.

5. Invalid numeric values
   Nonpositive ClosePrice and LivingArea values, negative DaysOnMarket values,
   and negative bedroom or bathroom counts were flagged. Invalid field values
   were replaced with missing values, but the full records were retained.

6. Date consistency
   Added listing_after_close_flag, purchase_after_close_flag, and
   negative_timeline_flag. The final flag also identifies ListingContractDate
   values that occur after PurchaseContractDate.

7. Geographic quality
   Added flags for missing coordinates, zero coordinates, positive longitude,
   and coordinates outside an approximate California bounding box (latitude
   32.0 to 42.1; longitude -124.5 to -114.0). Coordinate issues were flagged,
   not removed, because non-geographic fields may remain useful.

8. Row preservation
   No entire rows were removed. Before/after row counts are validated and saved
   in week4_5_dataset_summary.csv.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    for input_path in [args.listings, args.sold]:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

    # Process and save one large dataset at a time to keep memory use manageable.
    print("Loading Week 3 enriched Listings dataset...")
    listings = pd.read_csv(args.listings, low_memory=False)
    print(f"Listings: {len(listings):,} rows, {len(listings.columns)} columns")
    print("Cleaning Listings...")
    clean_listings, listings_reports = clean_dataset(listings, "listings")
    listings_output = args.outdir / "listings_residential_week4_5_clean.csv"
    clean_listings.to_csv(listings_output, index=False, date_format="%Y-%m-%d")
    del listings, clean_listings

    print("\nLoading Week 3 enriched Sold dataset...")
    sold = pd.read_csv(args.sold, low_memory=False)
    print(f"Sold: {len(sold):,} rows, {len(sold.columns)} columns")
    print("Cleaning Sold...")
    clean_sold, sold_reports = clean_dataset(sold, "sold")
    sold_output = args.outdir / "sold_residential_week4_5_clean.csv"
    clean_sold.to_csv(sold_output, index=False, date_format="%Y-%m-%d")
    del sold, clean_sold

    all_reports = {}
    for key in listings_reports:
        all_reports[key] = listings_reports[key] + sold_reports[key]

    report_paths = {
        "dataset": args.outdir / "week4_5_dataset_summary.csv",
        "types": args.outdir / "week4_5_data_type_confirmation.csv",
        "numeric": args.outdir / "week4_5_numeric_quality_summary.csv",
        "dates": args.outdir / "week4_5_date_consistency_summary.csv",
        "geographic": args.outdir / "week4_5_geographic_quality_summary.csv",
        "redundant": args.outdir / "week4_5_redundant_columns_report.csv",
    }
    for key, output_path in report_paths.items():
        pd.DataFrame(all_reports[key]).to_csv(output_path, index=False)

    transformation_log = args.outdir / "week4_5_transformation_log.txt"
    write_transformation_log(transformation_log)

    dataset_summary = pd.DataFrame(all_reports["dataset"])
    date_summary = pd.DataFrame(all_reports["dates"])
    geographic_summary = pd.DataFrame(all_reports["geographic"])
    numeric_summary = pd.DataFrame(all_reports["numeric"])

    print("\nBefore/after summary:")
    print(dataset_summary.to_string(index=False))
    print("\nDate consistency flags:")
    print(date_summary.to_string(index=False))
    print("\nGeographic quality flags:")
    print(geographic_summary.to_string(index=False))
    print("\nInvalid numeric values:")
    print(numeric_summary.to_string(index=False))

    print("\nWeeks 4-5 cleaning completed successfully.")
    print(f"Saved {listings_output}")
    print(f"Saved {sold_output}")
    for output_path in report_paths.values():
        print(f"Saved {output_path}")
    print(f"Saved {transformation_log}")


if __name__ == "__main__":
    main()
