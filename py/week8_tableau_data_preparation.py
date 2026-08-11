"""Week 8: prepare one Tableau-ready market analysis event table.

Inputs created in earlier internship weeks:
    processed/listings_residential_week4_5_clean.csv
    processed/sold_residential_week7_filtered.csv

Main output:
    processed/tableau_market_events_week8.csv

Validation outputs:
    processed/week8_tableau_preparation_summary.csv
    processed/week8_tableau_field_coverage.csv
    processed/week8_ratio_cleaning_summary.csv

The long-format output contains one row per market event:
* New Listing events use ListingContractDate.
* Closed Sale events use CloseDate and carry the sold-market measures.

This structure lets all five required Week 8 market worksheets use the same
month, city, county, ZIP code, and PropertySubType filters in Tableau. Sold
measures are intentionally missing on New Listing rows, so Tableau ignores
those rows when calculating sold-market medians and averages.

For the close-to-original-list ratio, values outside 0.50-1.50 are set to
missing in the Tableau output. This wide, domain-based plausibility range
prevents placeholder OriginalListPrice values (for example, $1) from
distorting the required monthly average. The sold event itself is retained for
all other measures, and the exclusions are documented in a separate report.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


START_DATE = pd.Timestamp("2024-01-01")
MIN_VALID_CLOSE_TO_ORIGINAL_RATIO = 0.50
MAX_VALID_CLOSE_TO_ORIGINAL_RATIO = 1.50

DIMENSION_COLUMNS = [
    "ListingKey",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertySubType",
]

LISTING_OPTIONAL_COLUMNS = [
    "PropertyType",
    "MLSAreaMajor",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "rate_30yr_fixed",
]

SOLD_MEASURE_COLUMNS = [
    "ClosePrice",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "PricePerSqFt",
]

SOLD_OPTIONAL_COLUMNS = [
    "PropertyType",
    "MLSAreaMajor",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "rate_30yr_fixed",
]

OUTPUT_COLUMNS = [
    "EventType",
    "EventDate",
    "EventMonth",
    "Year",
    "Month",
    "YrMo",
    "EventCount",
    "ListingKey",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertyType",
    "PropertySubType",
    "MLSAreaMajor",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "ClosePrice",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "PricePerSqFt",
    "rate_30yr_fixed",
]

NUMERIC_OUTPUT_COLUMNS = {
    "EventCount",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "ClosePrice",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "PricePerSqFt",
    "rate_30yr_fixed",
}


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "py" else script_dir
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Create the long-format Week 8 Tableau market data source."
    )
    parser.add_argument(
        "--listings",
        type=Path,
        default=processed_dir / "listings_residential_week4_5_clean.csv",
        help="Path to the cleaned Residential Listings CSV from Weeks 4-5.",
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week7_filtered.csv",
        help="Path to the filtered Residential Sold CSV from Week 7.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=processed_dir,
        help="Directory for the Week 8 Tableau CSV and validation reports.",
    )
    return parser.parse_args()


def available_columns(path: Path) -> list[str]:
    """Read only the header before loading the required source columns."""
    return pd.read_csv(path, nrows=0).columns.tolist()


def load_selected_columns(
    path: Path,
    required: list[str],
    optional: list[str],
    dataset_name: str,
) -> pd.DataFrame:
    columns = available_columns(path)
    missing = [column for column in required if column not in columns]
    if missing:
        raise KeyError(
            f"{dataset_name} is missing required Week 8 columns: {missing}"
        )

    selected = required + [column for column in optional if column in columns]
    string_columns = {
        column: "string"
        for column in [
            "ListingKey",
            "City",
            "CountyOrParish",
            "PostalCode",
            "PropertyType",
            "PropertySubType",
            "MLSAreaMajor",
        ]
        if column in selected
    }
    return pd.read_csv(
        path,
        usecols=selected,
        dtype=string_columns,
        low_memory=False,
    )


def clean_text_dimension(values: pd.Series) -> pd.Series:
    cleaned = values.astype("string").str.strip()
    return cleaned.mask(cleaned.eq(""))


def clean_postal_code(values: pd.Series) -> pd.Series:
    """Return a five-digit ZIP when possible and preserve other valid text."""
    cleaned = clean_text_dimension(values).str.replace(r"\.0$", "", regex=True)
    five_digit = cleaned.str.extract(r"(\d{5})", expand=False)
    return five_digit.fillna(cleaned)


def add_missing_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    for column in OUTPUT_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = (
                float("nan") if column in NUMERIC_OUTPUT_COLUMNS else pd.NA
            )
    return prepared


def standardize_common_fields(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    for column in [
        "ListingKey",
        "City",
        "CountyOrParish",
        "PropertyType",
        "PropertySubType",
        "MLSAreaMajor",
    ]:
        if column in prepared.columns:
            prepared[column] = clean_text_dimension(prepared[column])

    prepared["PostalCode"] = clean_postal_code(prepared["PostalCode"])

    for column in [
        "Latitude",
        "Longitude",
        "ListPrice",
        "OriginalListPrice",
        "ClosePrice",
        "DaysOnMarket",
        "CloseToOriginalListRatio",
        "PricePerSqFt",
        "rate_30yr_fixed",
    ]:
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    return prepared


def add_event_date_fields(
    df: pd.DataFrame, source_date: str, event_type: str
) -> pd.DataFrame:
    prepared = df.copy()
    prepared["EventDate"] = pd.to_datetime(
        prepared[source_date], errors="coerce"
    )
    prepared = prepared.loc[prepared["EventDate"] >= START_DATE].copy()
    prepared["EventType"] = event_type
    prepared["EventMonth"] = prepared["EventDate"].dt.to_period("M").dt.to_timestamp()
    prepared["Year"] = prepared["EventDate"].dt.year.astype("Int64")
    prepared["Month"] = prepared["EventDate"].dt.month.astype("Int64")
    prepared["YrMo"] = prepared["EventDate"].dt.strftime("%Y-%m")
    prepared["EventCount"] = 1
    return prepared.drop(columns=source_date)


def prepare_listing_events(listings: pd.DataFrame) -> pd.DataFrame:
    prepared = standardize_common_fields(listings)
    prepared = add_event_date_fields(
        prepared, "ListingContractDate", "New Listing"
    )
    return add_missing_output_columns(prepared)[OUTPUT_COLUMNS]


def prepare_sold_events(sold: pd.DataFrame) -> pd.DataFrame:
    prepared = standardize_common_fields(sold)
    prepared = add_event_date_fields(prepared, "CloseDate", "Closed Sale")
    return add_missing_output_columns(prepared)[OUTPUT_COLUMNS]


def clean_ratio_for_analysis(
    sold_events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exclude implausible ratios without deleting their closed-sale rows."""
    prepared = sold_events.copy()
    ratio = prepared["CloseToOriginalListRatio"]
    non_missing = ratio.notna()
    below_bound = non_missing & ratio.lt(MIN_VALID_CLOSE_TO_ORIGINAL_RATIO)
    above_bound = non_missing & ratio.gt(MAX_VALID_CLOSE_TO_ORIGINAL_RATIO)
    excluded = below_bound | above_bound

    prepared.loc[excluded, "CloseToOriginalListRatio"] = float("nan")

    valid_rows = int(prepared["CloseToOriginalListRatio"].notna().sum())
    report = pd.DataFrame(
        [
            {
                "field": "CloseToOriginalListRatio",
                "lower_bound_inclusive": MIN_VALID_CLOSE_TO_ORIGINAL_RATIO,
                "upper_bound_inclusive": MAX_VALID_CLOSE_TO_ORIGINAL_RATIO,
                "sold_event_rows": len(prepared),
                "non_missing_before_cleaning": int(non_missing.sum()),
                "missing_before_cleaning": int((~non_missing).sum()),
                "excluded_below_lower_bound": int(below_bound.sum()),
                "excluded_above_upper_bound": int(above_bound.sum()),
                "total_excluded_as_implausible": int(excluded.sum()),
                "valid_rows_after_cleaning": valid_rows,
                "missing_after_cleaning": int(len(prepared) - valid_rows),
                "valid_percent_after_cleaning": round(
                    valid_rows / len(prepared) * 100, 2
                )
                if len(prepared)
                else 0.0,
            }
        ]
    )
    return prepared, report


def create_preparation_summary(
    source_listing_rows: int,
    source_sold_rows: int,
    listing_events: pd.DataFrame,
    sold_events: pd.DataFrame,
    combined: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for dataset, source_rows, events in [
        ("new_listing_events", source_listing_rows, listing_events),
        ("closed_sale_events", source_sold_rows, sold_events),
        ("combined_tableau_events", source_listing_rows + source_sold_rows, combined),
    ]:
        non_missing_keys = events.loc[events["ListingKey"].notna()].copy()
        duplicate_identity_rows = non_missing_keys.duplicated(
            subset=["EventType", "ListingKey"], keep=False
        )
        rows.append(
            {
                "dataset": dataset,
                "source_rows": source_rows,
                "output_rows_from_2024_01": len(events),
                "rows_excluded_before_2024_or_missing_date": source_rows
                - len(events),
                "earliest_event_date": events["EventDate"].min(),
                "latest_event_date": events["EventDate"].max(),
                "distinct_listing_keys": events["ListingKey"].nunique(
                    dropna=True
                ),
                "missing_listing_keys": int(events["ListingKey"].isna().sum()),
                "duplicate_event_identity_rows": int(
                    duplicate_identity_rows.sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def create_field_coverage(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event_type, group in events.groupby("EventType", sort=False):
        for field in [
            "City",
            "CountyOrParish",
            "PostalCode",
            "PropertySubType",
            "ClosePrice",
            "DaysOnMarket",
            "CloseToOriginalListRatio",
        ]:
            populated = int(group[field].notna().sum())
            rows.append(
                {
                    "event_type": event_type,
                    "field": field,
                    "row_count": len(group),
                    "populated_rows": populated,
                    "missing_rows": len(group) - populated,
                    "populated_percent": round(populated / len(group) * 100, 2)
                    if len(group)
                    else 0.0,
                }
            )
    return pd.DataFrame(rows)


def validate_tableau_output(
    listing_events: pd.DataFrame,
    sold_events: pd.DataFrame,
    combined: pd.DataFrame,
) -> None:
    if listing_events.empty:
        raise ValueError("No New Listing events remain from January 2024 onward.")
    if sold_events.empty:
        raise ValueError("No Closed Sale events remain from January 2024 onward.")
    if len(combined) != len(listing_events) + len(sold_events):
        raise ValueError("The combined Tableau row count does not reconcile.")
    if combined["EventDate"].isna().any():
        raise ValueError("The Tableau event table contains a missing EventDate.")
    if (combined["EventDate"] < START_DATE).any():
        raise ValueError("The Tableau event table contains a pre-2024 event.")
    if not set(combined["EventType"].unique()) == {
        "New Listing",
        "Closed Sale",
    }:
        raise ValueError("The Tableau event types are incomplete or unexpected.")
    if listing_events[SOLD_MEASURE_COLUMNS].notna().any().any():
        raise ValueError("New Listing rows unexpectedly contain sold measures.")
    if combined["EventCount"].ne(1).any():
        raise ValueError("EventCount must equal 1 on every Tableau row.")


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    for path in [args.listings, args.sold]:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

    print(f"Loading Listings fields from {args.listings}...")
    listings = load_selected_columns(
        args.listings,
        required=DIMENSION_COLUMNS + ["ListingContractDate"],
        optional=LISTING_OPTIONAL_COLUMNS,
        dataset_name="Listings dataset",
    )
    print(f"Loaded {len(listings):,} Listings rows.")

    print(f"Loading Sold fields from {args.sold}...")
    sold = load_selected_columns(
        args.sold,
        required=DIMENSION_COLUMNS + ["CloseDate"] + SOLD_MEASURE_COLUMNS,
        optional=SOLD_OPTIONAL_COLUMNS,
        dataset_name="Sold dataset",
    )
    print(f"Loaded {len(sold):,} Sold rows.")

    listing_events = prepare_listing_events(listings)
    sold_events = prepare_sold_events(sold)
    sold_events, ratio_cleaning = clean_ratio_for_analysis(sold_events)
    combined = pd.concat([listing_events, sold_events], ignore_index=True)
    combined = combined.sort_values(
        ["EventDate", "EventType", "ListingKey"],
        kind="stable",
        na_position="last",
    ).reset_index(drop=True)

    validate_tableau_output(listing_events, sold_events, combined)
    summary = create_preparation_summary(
        len(listings),
        len(sold),
        listing_events,
        sold_events,
        combined,
    )
    coverage = create_field_coverage(combined)

    tableau_output = args.outdir / "tableau_market_events_week8.csv"
    summary_output = args.outdir / "week8_tableau_preparation_summary.csv"
    coverage_output = args.outdir / "week8_tableau_field_coverage.csv"
    ratio_cleaning_output = args.outdir / "week8_ratio_cleaning_summary.csv"

    combined.to_csv(tableau_output, index=False, date_format="%Y-%m-%d")
    summary.to_csv(summary_output, index=False, date_format="%Y-%m-%d")
    coverage.to_csv(coverage_output, index=False)
    ratio_cleaning.to_csv(ratio_cleaning_output, index=False)

    print("\nWeek 8 Tableau preparation summary:")
    print(summary.to_string(index=False))
    print("\nClose-to-original-list ratio cleaning summary:")
    print(ratio_cleaning.to_string(index=False))
    print("\nWeek 8 Tableau data preparation completed successfully.")
    print(f"Saved {tableau_output}")
    print(f"Saved {summary_output}")
    print(f"Saved {coverage_output}")
    print(f"Saved {ratio_cleaning_output}")


if __name__ == "__main__":
    main()
