import pandas as pd
from pathlib import Path

# -----------------------------
# Paths
# -----------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "processed"

LISTINGS_PATH = PROCESSED_DIR / "combined_listings_residential.csv"
SOLD_PATH = PROCESSED_DIR / "combined_sold_residential.csv"

LISTINGS_REPORT_PATH = PROCESSED_DIR / "week2_listing_missingness_report.csv"
SOLD_REPORT_PATH = PROCESSED_DIR / "week2_sold_missingness_report.csv"
SUMMARY_PATH = PROCESSED_DIR / "week2_dataset_summary.txt"


# -----------------------------
# Helper functions
# -----------------------------

def load_dataset(path):
    print(f"\nLoading: {path}")
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded {df.shape[0]:,} rows and {df.shape[1]:,} columns.")
    return df


def create_missingness_report(df):
    report = pd.DataFrame({
        "column": df.columns,
        "missing_count": df.isna().sum().values,
        "missing_percent": (df.isna().mean().values * 100).round(2),
        "non_missing_count": df.notna().sum().values
    })

    report["above_90_percent_missing"] = report["missing_percent"] > 90

    report = report.sort_values(
        by=["missing_percent", "missing_count"],
        ascending=[False, False]
    )

    return report


def summarize_dataset(name, df, missing_report):
    lines = []

    lines.append(f"{name} Dataset Summary")
    lines.append("-" * 40)
    lines.append(f"Rows: {df.shape[0]:,}")
    lines.append(f"Columns: {df.shape[1]:,}")

    if "PropertyType" in df.columns:
        lines.append("\nUnique PropertyType values:")
        property_counts = df["PropertyType"].value_counts(dropna=False)
        for value, count in property_counts.items():
            lines.append(f"  {value}: {count:,}")
    else:
        lines.append("\nPropertyType column not found.")

    high_missing = missing_report[missing_report["above_90_percent_missing"]]

    lines.append(f"\nColumns above 90% missing: {len(high_missing)}")

    if len(high_missing) > 0:
        lines.append("Columns above 90% missing:")
        for _, row in high_missing.iterrows():
            lines.append(
                f"  {row['column']}: {row['missing_percent']}% missing"
            )

    lines.append("\nTop 20 columns by missing percentage:")
    top_20 = missing_report.head(20)
    for _, row in top_20.iterrows():
        lines.append(
            f"  {row['column']}: {row['missing_percent']}% missing"
        )

    return "\n".join(lines)


# -----------------------------
# Main
# -----------------------------

def main():
    listings = load_dataset(LISTINGS_PATH)
    sold = load_dataset(SOLD_PATH)

    print("\nCreating missingness reports...")

    listings_missing_report = create_missingness_report(listings)
    sold_missing_report = create_missingness_report(sold)

    listings_missing_report.to_csv(LISTINGS_REPORT_PATH, index=False)
    sold_missing_report.to_csv(SOLD_REPORT_PATH, index=False)

    print(f"Saved listing missingness report to: {LISTINGS_REPORT_PATH}")
    print(f"Saved sold missingness report to: {SOLD_REPORT_PATH}")

    listings_summary = summarize_dataset(
        "Listings",
        listings,
        listings_missing_report
    )

    sold_summary = summarize_dataset(
        "Sold",
        sold,
        sold_missing_report
    )

    full_summary = listings_summary + "\n\n" + "=" * 60 + "\n\n" + sold_summary

    SUMMARY_PATH.write_text(full_summary, encoding="utf-8")

    print(f"Saved dataset summary to: {SUMMARY_PATH}")

    print("\nWeek 2 data audit completed successfully.")


if __name__ == "__main__":
    main()