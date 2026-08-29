"""Weeks 9-10: prepare a Tableau-ready competitive analysis dataset.

Input (created in Week 7):
    processed/sold_residential_week7_filtered.csv

Main output:
    processed/tableau_competitive_week9_10.csv

Validation outputs:
    processed/week9_10_competitive_preparation_summary.csv
    processed/week9_10_competitive_field_coverage.csv
    processed/week9_10_duplicate_listingkey_summary.csv

The output is designed for the competitive_analysis.twbx workbook required in
Weeks 8-10 of the IDX Exchange internship handbook. It supports:
* Top 100 listing agents by sales volume and units
* Top 100 listing offices by sales volume and units
* ZIP-code map of median close prices
* ZIP-code map of homes sold
* Shared filters for month, city, county, ZIP code, and PropertySubType

SalesVolume is ClosePrice and UnitCount is 1 per prepared closed-sale row.
Non-missing duplicate ListingKey values are de-duplicated so the same MLS
listing does not inflate competitive rankings or ZIP-level totals. Missing
ListingKey rows are retained because they cannot be safely identified as
duplicates. Duplicate handling is documented in the summary outputs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


START_DATE = pd.Timestamp("2024-01-01")

CORE_REQUIRED = [
    "CloseDate",
    "ClosePrice",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertySubType",
    "ListOfficeName",
]

OPTIONAL_FIELDS = [
    "ListingKey",
    "PropertyType",
    "MLSAreaMajor",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "PricePerSqFt",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "rate_30yr_fixed",
    "ListAgentKey",
    "ListAgentMlsId",
    "ListAgentEmail",
    "ListAgentFullName",
    "ListAgentFirstName",
    "ListAgentLastName",
]

OUTPUT_COLUMNS = [
    "TransactionKey",
    "ListingKey",
    "CloseDate",
    "CloseMonth",
    "Year",
    "Month",
    "YrMo",
    "UnitCount",
    "SalesVolume",
    "ClosePrice",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertyType",
    "PropertySubType",
    "MLSAreaMajor",
    "Latitude",
    "Longitude",
    "ListingAgent",
    "ListingAgentKey",
    "ListAgentEmail",
    "ListOfficeName",
    "ListPrice",
    "OriginalListPrice",
    "PricePerSqFt",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "rate_30yr_fixed",
]

TEXT_FIELDS = [
    "ListingKey",
    "City",
    "CountyOrParish",
    "PostalCode",
    "PropertyType",
    "PropertySubType",
    "MLSAreaMajor",
    "ListOfficeName",
    "ListAgentKey",
    "ListAgentMlsId",
    "ListAgentEmail",
    "ListAgentFullName",
    "ListAgentFirstName",
    "ListAgentLastName",
]

NUMERIC_FIELDS = [
    "ClosePrice",
    "Latitude",
    "Longitude",
    "ListPrice",
    "OriginalListPrice",
    "PricePerSqFt",
    "DaysOnMarket",
    "CloseToOriginalListRatio",
    "rate_30yr_fixed",
]


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "py" else script_dir
    processed_dir = project_root / "processed"

    parser = argparse.ArgumentParser(
        description="Prepare the Weeks 9-10 Tableau competitive data source."
    )
    parser.add_argument(
        "--sold",
        type=Path,
        default=processed_dir / "sold_residential_week7_filtered.csv",
        help="Path to the Week 7 filtered Residential Sold CSV.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=processed_dir,
        help="Directory for Tableau data and validation reports.",
    )
    return parser.parse_args()


def clean_text(values: pd.Series) -> pd.Series:
    cleaned = values.astype("string").str.strip()
    return cleaned.mask(cleaned.eq(""))


def clean_postal_code(values: pd.Series) -> pd.Series:
    cleaned = clean_text(values).str.replace(r"\.0$", "", regex=True)
    five_digit = cleaned.str.extract(r"(\d{5})", expand=False)
    return five_digit.fillna(cleaned)


def available_columns(path: Path) -> list[str]:
    return pd.read_csv(path, nrows=0).columns.tolist()


def load_source(path: Path) -> pd.DataFrame:
    columns = available_columns(path)
    missing = [field for field in CORE_REQUIRED if field not in columns]
    if missing:
        raise KeyError(f"Sold dataset is missing required fields: {missing}")

    selected = CORE_REQUIRED + [
        field for field in OPTIONAL_FIELDS
        if field in columns and field not in CORE_REQUIRED
    ]
    dtype_map = {field: "string" for field in TEXT_FIELDS if field in selected}
    return pd.read_csv(
        path,
        usecols=selected,
        dtype=dtype_map,
        low_memory=False,
    )


def standardize_fields(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    for field in TEXT_FIELDS:
        if field in prepared.columns:
            prepared[field] = clean_text(prepared[field])

    prepared["PostalCode"] = clean_postal_code(prepared["PostalCode"])

    for field in NUMERIC_FIELDS:
        if field in prepared.columns:
            prepared[field] = pd.to_numeric(prepared[field], errors="coerce")

    prepared["CloseDate"] = pd.to_datetime(prepared["CloseDate"], errors="coerce")
    return prepared


def build_agent_fields(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()

    if "ListAgentFullName" in prepared.columns:
        full_name = clean_text(prepared["ListAgentFullName"])
    else:
        full_name = pd.Series(pd.NA, index=prepared.index, dtype="string")

    if {"ListAgentFirstName", "ListAgentLastName"}.issubset(prepared.columns):
        first = prepared["ListAgentFirstName"].fillna("")
        last = prepared["ListAgentLastName"].fillna("")
        combined_name = (first + " " + last).str.strip().astype("string")
        combined_name = combined_name.mask(combined_name.eq(""))
        full_name = full_name.fillna(combined_name)

    email = (
        prepared["ListAgentEmail"]
        if "ListAgentEmail" in prepared.columns
        else pd.Series(pd.NA, index=prepared.index, dtype="string")
    )
    mls_id = (
        prepared["ListAgentMlsId"]
        if "ListAgentMlsId" in prepared.columns
        else pd.Series(pd.NA, index=prepared.index, dtype="string")
    )
    raw_key = (
        prepared["ListAgentKey"]
        if "ListAgentKey" in prepared.columns
        else pd.Series(pd.NA, index=prepared.index, dtype="string")
    )

    listing_agent = full_name.fillna(email).fillna(mls_id).fillna(raw_key)
    listing_agent = listing_agent.fillna("Unknown Agent")

    # Prefer a stable key when one is available; otherwise use progressively
    # less stable identifiers so Tableau can still group agent records.
    listing_agent_key = raw_key.fillna(mls_id).fillna(email).fillna(full_name)
    listing_agent_key = listing_agent_key.fillna("Unknown Agent")

    prepared["ListingAgent"] = listing_agent
    prepared["ListingAgentKey"] = listing_agent_key

    if "ListAgentEmail" not in prepared.columns:
        prepared["ListAgentEmail"] = pd.NA

    return prepared


def duplicate_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "ListingKey" not in df.columns:
        return pd.DataFrame(
            [{
                "listing_key_available": False,
                "source_rows": len(df),
                "missing_listing_keys": len(df),
                "duplicate_listingkey_rows": 0,
                "duplicate_listingkey_values": 0,
                "conflicting_closeprice_duplicate_keys": 0,
                "conflicting_agent_duplicate_keys": 0,
                "conflicting_office_duplicate_keys": 0,
            }]
        )

    keyed = df[df["ListingKey"].notna()].copy()
    duplicated = keyed[keyed.duplicated("ListingKey", keep=False)].copy()

    if duplicated.empty:
        conflict_price = conflict_agent = conflict_office = 0
    else:
        grouped = duplicated.groupby("ListingKey", dropna=False)
        conflict_price = int((grouped["ClosePrice"].nunique(dropna=True) > 1).sum())
        conflict_agent = int((grouped["ListingAgentKey"].nunique(dropna=True) > 1).sum())
        conflict_office = int((grouped["ListOfficeName"].nunique(dropna=True) > 1).sum())

    return pd.DataFrame(
        [{
            "listing_key_available": True,
            "source_rows": len(df),
            "missing_listing_keys": int(df["ListingKey"].isna().sum()),
            "duplicate_listingkey_rows": len(duplicated),
            "duplicate_listingkey_values": int(duplicated["ListingKey"].nunique()),
            "conflicting_closeprice_duplicate_keys": conflict_price,
            "conflicting_agent_duplicate_keys": conflict_agent,
            "conflicting_office_duplicate_keys": conflict_office,
        }]
    )


def deduplicate_listing_keys(df: pd.DataFrame) -> pd.DataFrame:
    if "ListingKey" not in df.columns:
        return df.copy()

    prepared = df.copy()
    prepared["_source_order"] = range(len(prepared))

    keyed = prepared[prepared["ListingKey"].notna()].copy()
    missing_key = prepared[prepared["ListingKey"].isna()].copy()

    # If repeated records exist, keep the latest CloseDate; for ties, preserve
    # the final source occurrence. This yields one competitive transaction per
    # non-missing MLS ListingKey without discarding rows whose key is missing.
    keyed = keyed.sort_values(
        ["ListingKey", "CloseDate", "_source_order"],
        kind="stable",
        na_position="first",
    )
    keyed = keyed.drop_duplicates("ListingKey", keep="last")

    combined = pd.concat([keyed, missing_key], ignore_index=True)
    combined = combined.sort_values("_source_order", kind="stable")
    return combined.drop(columns="_source_order").reset_index(drop=True)


def add_tableau_fields(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared = prepared.loc[prepared["CloseDate"] >= START_DATE].copy()
    prepared = prepared.loc[prepared["ClosePrice"].notna()].copy()

    prepared["CloseMonth"] = prepared["CloseDate"].dt.to_period("M").dt.to_timestamp()
    prepared["Year"] = prepared["CloseDate"].dt.year.astype("Int64")
    prepared["Month"] = prepared["CloseDate"].dt.month.astype("Int64")
    prepared["YrMo"] = prepared["CloseDate"].dt.strftime("%Y-%m")
    prepared["UnitCount"] = 1
    prepared["SalesVolume"] = prepared["ClosePrice"]

    if "ListingKey" not in prepared.columns:
        prepared["ListingKey"] = pd.NA

    # Every row needs a transaction identifier. Use ListingKey when available;
    # otherwise use a deterministic missing-key surrogate based on row order.
    surrogate = pd.Series(
        [f"MISSINGKEY_{i:07d}" for i in range(1, len(prepared) + 1)],
        index=prepared.index,
        dtype="string",
    )
    prepared["TransactionKey"] = prepared["ListingKey"].fillna(surrogate)

    for field in OUTPUT_COLUMNS:
        if field not in prepared.columns:
            prepared[field] = pd.NA

    return prepared[OUTPUT_COLUMNS]


def make_summary(
    source_rows: int,
    standardized_rows: int,
    prepared: pd.DataFrame,
    duplicates: pd.DataFrame,
) -> pd.DataFrame:
    dup = duplicates.iloc[0].to_dict()
    return pd.DataFrame(
        [{
            "source_rows": source_rows,
            "rows_after_type_and_text_standardization": standardized_rows,
            "rows_after_2024_price_filter_and_listingkey_deduplication": len(prepared),
            "rows_removed_or_collapsed": source_rows - len(prepared),
            "earliest_close_date": prepared["CloseDate"].min(),
            "latest_close_date": prepared["CloseDate"].max(),
            "distinct_transaction_keys": prepared["TransactionKey"].nunique(dropna=True),
            "distinct_listing_agents": prepared["ListingAgentKey"].nunique(dropna=True),
            "distinct_listing_offices": prepared["ListOfficeName"].nunique(dropna=True),
            "distinct_zip_codes": prepared["PostalCode"].nunique(dropna=True),
            "duplicate_listingkey_rows_before_deduplication": dup.get("duplicate_listingkey_rows", 0),
            "duplicate_listingkey_values_before_deduplication": dup.get("duplicate_listingkey_values", 0),
            "conflicting_closeprice_duplicate_keys": dup.get("conflicting_closeprice_duplicate_keys", 0),
            "conflicting_agent_duplicate_keys": dup.get("conflicting_agent_duplicate_keys", 0),
            "conflicting_office_duplicate_keys": dup.get("conflicting_office_duplicate_keys", 0),
        }]
    )


def field_coverage(df: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "ListingAgent",
        "ListingAgentKey",
        "ListOfficeName",
        "City",
        "CountyOrParish",
        "PostalCode",
        "PropertySubType",
        "ClosePrice",
        "CloseDate",
    ]
    rows = []
    for field in fields:
        populated = int(df[field].notna().sum())
        rows.append(
            {
                "field": field,
                "row_count": len(df),
                "populated_rows": populated,
                "missing_rows": len(df) - populated,
                "populated_percent": round(populated / len(df) * 100, 2)
                if len(df)
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def validate_output(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Competitive Tableau output is empty.")
    if df["CloseDate"].isna().any():
        raise ValueError("A prepared competitive row has a missing CloseDate.")
    if (df["CloseDate"] < START_DATE).any():
        raise ValueError("A prepared competitive row predates January 2024.")
    if df["ClosePrice"].isna().any():
        raise ValueError("A prepared competitive row has a missing ClosePrice.")
    if df["SalesVolume"].ne(df["ClosePrice"]).any():
        raise ValueError("SalesVolume must equal ClosePrice on every row.")
    if df["UnitCount"].ne(1).any():
        raise ValueError("UnitCount must equal 1 on every row.")
    if df["TransactionKey"].duplicated().any():
        raise ValueError("TransactionKey is not unique after preparation.")


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    if not args.sold.exists():
        raise FileNotFoundError(f"Input file not found: {args.sold}")

    print(f"Loading {args.sold}...")
    sold = load_source(args.sold)
    print(f"Loaded {len(sold):,} Sold rows and {len(sold.columns)} selected columns.")

    standardized = standardize_fields(sold)
    standardized = build_agent_fields(standardized)
    duplicates = duplicate_summary(standardized)
    deduplicated = deduplicate_listing_keys(standardized)
    competitive = add_tableau_fields(deduplicated)
    validate_output(competitive)

    summary = make_summary(
        source_rows=len(sold),
        standardized_rows=len(standardized),
        prepared=competitive,
        duplicates=duplicates,
    )
    coverage = field_coverage(competitive)

    output = args.outdir / "tableau_competitive_week9_10.csv"
    summary_output = args.outdir / "week9_10_competitive_preparation_summary.csv"
    coverage_output = args.outdir / "week9_10_competitive_field_coverage.csv"
    duplicate_output = args.outdir / "week9_10_duplicate_listingkey_summary.csv"

    competitive.to_csv(output, index=False, date_format="%Y-%m-%d")
    summary.to_csv(summary_output, index=False, date_format="%Y-%m-%d")
    coverage.to_csv(coverage_output, index=False)
    duplicates.to_csv(duplicate_output, index=False)

    print("\nWeeks 9-10 competitive preparation summary:")
    print(summary.to_string(index=False))
    print("\nCompetitive field coverage:")
    print(coverage.to_string(index=False))
    print("\nDuplicate ListingKey review before de-duplication:")
    print(duplicates.to_string(index=False))

    print("\nWeeks 9-10 competitive Tableau preparation completed successfully.")
    print(f"Saved {output}")
    print(f"Saved {summary_output}")
    print(f"Saved {coverage_output}")
    print(f"Saved {duplicate_output}")


if __name__ == "__main__":
    main()
