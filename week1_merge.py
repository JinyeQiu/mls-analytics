from pathlib import Path
import pandas as pd


# ------------------------------------------------------------
# Week 1 - Monthly Dataset Aggregation
# IDX Exchange MLS Analytics Internship
#
# Purpose:
# Combine monthly CRMLS Listing and Sold CSV files into two
# Residential-only datasets for later cleaning and analysis.
#
# Notes:
# - Raw CSV files are stored locally in the csv/ folder.
# - Raw CSV files should NOT be uploaded to GitHub.
# - Processed output CSVs should also stay local.
# ------------------------------------------------------------


# Locate project folders
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

csv_dir = project_root / "csv"
processed_dir = project_root / "processed"
processed_dir.mkdir(exist_ok=True)


# ------------------------------------------------------------
# Step 1: Find listing files
# ------------------------------------------------------------

listing_files = sorted(csv_dir.glob("CRMLSListing*.csv"))

print("Listing files found:")
for file in listing_files:
    print(f"  {file.name}")

print(f"\nTotal listing files: {len(listing_files)}")


# ------------------------------------------------------------
# Step 2: Select sold files
#
# Some sold files have both regular and _filled versions.
# Based on mentor guidance, if a _filled version exists,
# we use the _filled version for that month to avoid duplication.
# ------------------------------------------------------------

all_sold_files = sorted(csv_dir.glob("CRMLSSold*.csv"))

sold_by_month = {}

for file in all_sold_files:
    # Example filenames:
    # CRMLSSold202401.csv
    # CRMLSSold202401_filled.csv

    month = file.stem.replace("CRMLSSold", "").replace("_filled", "")

    if month not in sold_by_month:
        sold_by_month[month] = file
    else:
        # Prefer _filled file when both versions exist
        if "_filled" in file.stem:
            sold_by_month[month] = file

sold_files = [sold_by_month[month] for month in sorted(sold_by_month.keys())]

print("\nSold files selected:")
for file in sold_files:
    print(f"  {file.name}")

print(f"\nTotal sold files selected: {len(sold_files)}")


# ------------------------------------------------------------
# Step 3: Helper function to combine files
# ------------------------------------------------------------

def combine_files(files, dataset_name):
    """
    Reads multiple CSV files and combines them into one DataFrame.
    Adds a source_file column so we can trace each row back to
    its original monthly CSV.
    """
    dataframes = []
    total_rows_before_concat = 0

    print(f"\nReading {dataset_name} files...")

    for file in files:
        df = pd.read_csv(file, low_memory=False)

        row_count = len(df)
        col_count = len(df.columns)

        print(f"  {file.name}: {row_count:,} rows, {col_count} columns")

        total_rows_before_concat += row_count

        # Track source file for validation and debugging
        df["source_file"] = file.name

        dataframes.append(df)

    combined = pd.concat(dataframes, ignore_index=True)

    print(f"\n{dataset_name} row count before concatenation check:")
    print(f"  Sum of monthly rows: {total_rows_before_concat:,}")
    print(f"  Combined rows:       {len(combined):,}")

    if total_rows_before_concat == len(combined):
        print("  Row count check: PASSED")
    else:
        print("  Row count check: WARNING - counts do not match")

    return combined


# ------------------------------------------------------------
# Step 4: Combine listings and sold data
# ------------------------------------------------------------

listings_combined = combine_files(listing_files, "Listings")
sold_combined = combine_files(sold_files, "Sold")


# ------------------------------------------------------------
# Step 5: Filter to Residential
# ------------------------------------------------------------

def filter_residential(df, dataset_name):
    """
    Filters the dataset to PropertyType == 'Residential'.
    Prints row counts before and after filtering.
    """
    if "PropertyType" not in df.columns:
        raise ValueError(f"PropertyType column not found in {dataset_name} dataset.")

    before_filter = len(df)

    residential = df[df["PropertyType"] == "Residential"].copy()

    after_filter = len(residential)

    print(f"\n{dataset_name} Residential filter:")
    print(f"  Rows before filter: {before_filter:,}")
    print(f"  Rows after filter:  {after_filter:,}")
    print(f"  Rows removed:       {before_filter - after_filter:,}")

    return residential


listings_residential = filter_residential(listings_combined, "Listings")
sold_residential = filter_residential(sold_combined, "Sold")


# ------------------------------------------------------------
# Step 6: Save output CSVs locally
# ------------------------------------------------------------

listings_output = processed_dir / "combined_listings_residential.csv"
sold_output = processed_dir / "combined_sold_residential.csv"

listings_residential.to_csv(listings_output, index=False)
sold_residential.to_csv(sold_output, index=False)

print("\nOutput files saved locally:")
print(f"  {listings_output}")
print(f"  {sold_output}")

print("\nWeek 1 aggregation complete.")