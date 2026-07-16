import pandas as pd
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "processed"

LISTINGS_PATH = PROCESSED_DIR / "combined_listings_residential.csv"
SOLD_PATH = PROCESSED_DIR / "combined_sold_residential.csv"

LISTINGS_MISSINGNESS_PATH = PROCESSED_DIR / "week2_listing_missingness_report.csv"
SOLD_MISSINGNESS_PATH = PROCESSED_DIR / "week2_sold_missingness_report.csv"

CLEAN_LISTINGS_PATH = PROCESSED_DIR / "listings_residential_week2_clean.csv"
CLEAN_SOLD_PATH = PROCESSED_DIR / "sold_residential_week2_clean.csv"

DROPPED_COLUMNS_REPORT_PATH = PROCESSED_DIR / "week2_dropped_columns_report.csv"


# -----------------------------
# Helper functions
# -----------------------------

def get_columns_to_drop(missingness_report_path, threshold=90):
    report = pd.read_csv(missingness_report_path)

    columns_to_drop = report.loc[
        report["missing_percent"] > threshold,
        "column"
    ].tolist()

    return columns_to_drop


def clean_dataset(df, columns_to_drop):
    existing_columns_to_drop = [
        col for col in columns_to_drop if col in df.columns
    ]

    cleaned_df = df.drop(columns=existing_columns_to_drop)

    return cleaned_df, existing_columns_to_drop


# -----------------------------
# Main
# -----------------------------

def main():
    print("Loading datasets...")

    listings = pd.read_csv(LISTINGS_PATH, low_memory=False)
    sold = pd.read_csv(SOLD_PATH, low_memory=False)

    print(f"Listings before cleaning: {listings.shape[0]:,} rows, {listings.shape[1]} columns")
    print(f"Sold before cleaning: {sold.shape[0]:,} rows, {sold.shape[1]} columns")

    print("\nIdentifying columns with more than 90% missing values...")

    listing_columns_to_drop = get_columns_to_drop(LISTINGS_MISSINGNESS_PATH)
    sold_columns_to_drop = get_columns_to_drop(SOLD_MISSINGNESS_PATH)

    print(f"Listing columns to drop: {len(listing_columns_to_drop)}")
    print(f"Sold columns to drop: {len(sold_columns_to_drop)}")

    print("\nCleaning datasets...")

    clean_listings, dropped_listing_columns = clean_dataset(
        listings,
        listing_columns_to_drop
    )

    clean_sold, dropped_sold_columns = clean_dataset(
        sold,
        sold_columns_to_drop
    )

    print(f"Listings after cleaning: {clean_listings.shape[0]:,} rows, {clean_listings.shape[1]} columns")
    print(f"Sold after cleaning: {clean_sold.shape[0]:,} rows, {clean_sold.shape[1]} columns")

    print("\nSaving cleaned datasets...")

    clean_listings.to_csv(CLEAN_LISTINGS_PATH, index=False)
    clean_sold.to_csv(CLEAN_SOLD_PATH, index=False)

    print(f"Saved cleaned listings to: {CLEAN_LISTINGS_PATH}")
    print(f"Saved cleaned sold data to: {CLEAN_SOLD_PATH}")

    print("\nSaving dropped columns report...")

    dropped_rows = []

    for col in dropped_listing_columns:
        dropped_rows.append({
            "dataset": "listings",
            "column": col,
            "reason": "More than 90% missing values"
        })

    for col in dropped_sold_columns:
        dropped_rows.append({
            "dataset": "sold",
            "column": col,
            "reason": "More than 90% missing values"
        })

    dropped_report = pd.DataFrame(dropped_rows)
    dropped_report.to_csv(DROPPED_COLUMNS_REPORT_PATH, index=False)

    print(f"Saved dropped columns report to: {DROPPED_COLUMNS_REPORT_PATH}")

    print("\nWeek 2 column cleaning completed successfully.")


if __name__ == "__main__":
    main()