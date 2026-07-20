"""Week 3: enrich residential MLS datasets with monthly mortgage rates.

Inputs (created in Week 2):
    processed/listings_residential_week2_clean.csv
    processed/sold_residential_week2_clean.csv

Outputs:
    processed/listings_residential_week3_enriched.csv
    processed/sold_residential_week3_enriched.csv
    processed/mortgage_rates_monthly.csv
    processed/week3_mortgage_merge_validation.csv

The mortgage-rate source is the FRED MORTGAGE30US series, which contains the
weekly U.S. average 30-year fixed mortgage rate. Weekly observations are
averaged within each calendar month before being joined to the MLS records.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"


def fetch_monthly_mortgage_rates(url: str = FRED_URL) -> pd.DataFrame:
    """Fetch weekly FRED observations and return one average rate per month."""
    mortgage = pd.read_csv(url)

    required = {"observation_date", "MORTGAGE30US"}
    missing = required.difference(mortgage.columns)
    if missing:
        raise ValueError(f"FRED data is missing required columns: {sorted(missing)}")

    mortgage = mortgage.rename(
        columns={"observation_date": "date", "MORTGAGE30US": "rate_30yr_fixed"}
    )
    mortgage["date"] = pd.to_datetime(mortgage["date"], errors="coerce")
    mortgage["rate_30yr_fixed"] = pd.to_numeric(
        mortgage["rate_30yr_fixed"], errors="coerce"
    )
    mortgage = mortgage.dropna(subset=["date", "rate_30yr_fixed"])
    mortgage["year_month"] = mortgage["date"].dt.strftime("%Y-%m")

    monthly = (
        mortgage.groupby("year_month", as_index=False)["rate_30yr_fixed"]
        .mean()
        .sort_values("year_month")
        .reset_index(drop=True)
    )
    monthly["rate_30yr_fixed"] = monthly["rate_30yr_fixed"].round(4)

    if monthly.empty or monthly["year_month"].duplicated().any():
        raise ValueError("Monthly mortgage-rate table failed validation.")

    return monthly


def enrich_dataset(
    data: pd.DataFrame,
    monthly_rates: pd.DataFrame,
    date_column: str,
    dataset_name: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add a year-month key and mortgage rate, then summarize merge quality."""
    if date_column not in data.columns:
        raise KeyError(
            f"{dataset_name} is missing required date column {date_column!r}."
        )

    enriched = data.copy()
    parsed_dates = pd.to_datetime(enriched[date_column], errors="coerce")
    enriched["year_month"] = parsed_dates.dt.strftime("%Y-%m")
    enriched = enriched.merge(
        monthly_rates,
        on="year_month",
        how="left",
        validate="many_to_one",
    )

    invalid_date_rows = int(parsed_dates.isna().sum())
    unmatched_rate_rows = int(enriched["rate_30yr_fixed"].isna().sum())
    report = {
        "dataset": dataset_name,
        "date_column": date_column,
        "row_count_before": len(data),
        "row_count_after": len(enriched),
        "invalid_or_missing_date_rows": invalid_date_rows,
        "unmatched_rate_rows": unmatched_rate_rows,
        "all_rows_matched": unmatched_rate_rows == 0,
        "earliest_year_month": enriched["year_month"].min(),
        "latest_year_month": enriched["year_month"].max(),
    }

    if len(enriched) != len(data):
        raise ValueError(f"{dataset_name}: row count changed during the merge.")

    return enriched, report


def parse_args() -> argparse.Namespace:
    # Match the folder convention used by the Week 0-2 scripts:
    # Files/py/ contains scripts and Files/processed/ contains generated CSVs.
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Merge monthly FRED mortgage rates into Week 2 MLS datasets."
    )
    parser.add_argument(
        "--listings",
        type=Path,
        default=processed_dir / "listings_residential_week2_clean.csv",
        help="Path to the Week 2 cleaned listings CSV.",
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week2_clean.csv",
        help="Path to the Week 2 cleaned sold CSV.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=processed_dir,
        help="Directory for Week 3 output files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    for path in (args.listings, args.sold):
        if not path.exists():
            raise FileNotFoundError(
                f"Input file not found: {path}\n"
                "Confirm the Week 2 cleaned CSVs are in the project's processed folder "
                "or pass the correct path."
            )

    print("Fetching weekly 30-year mortgage rates from FRED...")
    monthly_rates = fetch_monthly_mortgage_rates()
    print(
        f"Created {len(monthly_rates):,} monthly averages: "
        f"{monthly_rates['year_month'].min()} to "
        f"{monthly_rates['year_month'].max()}"
    )

    print("Loading Week 2 residential datasets...")
    listings = pd.read_csv(args.listings, low_memory=False)
    sold = pd.read_csv(args.sold, low_memory=False)

    listings_enriched, listings_report = enrich_dataset(
        listings,
        monthly_rates,
        date_column="ListingContractDate",
        dataset_name="listings",
    )
    sold_enriched, sold_report = enrich_dataset(
        sold,
        monthly_rates,
        date_column="CloseDate",
        dataset_name="sold",
    )

    listings_output = args.outdir / "listings_residential_week3_enriched.csv"
    sold_output = args.outdir / "sold_residential_week3_enriched.csv"
    rates_output = args.outdir / "mortgage_rates_monthly.csv"
    validation_output = args.outdir / "week3_mortgage_merge_validation.csv"

    listings_enriched.to_csv(listings_output, index=False)
    sold_enriched.to_csv(sold_output, index=False)
    monthly_rates.to_csv(rates_output, index=False)

    validation = pd.DataFrame([listings_report, sold_report])
    validation.to_csv(validation_output, index=False)

    print("\nMerge validation:")
    print(validation.to_string(index=False))

    unmatched_total = int(validation["unmatched_rate_rows"].sum())
    if unmatched_total:
        unmatched = []
        for name, frame in (
            ("listings", listings_enriched),
            ("sold", sold_enriched),
        ):
            months = sorted(
                frame.loc[frame["rate_30yr_fixed"].isna(), "year_month"]
                .dropna()
                .unique()
            )
            unmatched.append(f"{name}: {months}")
        raise ValueError(
            f"Validation failed: {unmatched_total:,} rows have no mortgage rate. "
            + " | ".join(unmatched)
        )

    print("\nValidation passed: every row has a mortgage rate and row counts match.")
    print(f"Saved {listings_output}")
    print(f"Saved {sold_output}")
    print(f"Saved {rates_output}")
    print(f"Saved {validation_output}")


if __name__ == "__main__":
    main()
