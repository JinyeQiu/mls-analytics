"""Weeks 2-3: numeric distribution review for the residential sold dataset.

This completes the numeric EDA portion of the Weeks 2-3 assignment by saving:
  * percentile and descriptive summaries for the requested numeric fields
  * IQR-based extreme-outlier counts for later cleaning decisions
  * one histogram and one boxplot per available field
  * answers to the handbook's suggested preliminary EDA questions

The script only identifies unusual values. It does not remove them; outlier
handling belongs to the later cleaning phase.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PROCESSED_DIR = PROJECT_ROOT / "processed"

SOLD_PATH = PROCESSED_DIR / "sold_residential_week2_clean.csv"
SUMMARY_PATH = PROCESSED_DIR / "week3_numeric_distribution_summary.csv"
OUTLIER_PATH = PROCESSED_DIR / "week3_numeric_outlier_summary.csv"
EDA_ANSWERS_PATH = PROCESSED_DIR / "week3_eda_answers.txt"
PLOTS_DIR = PROCESSED_DIR / "week3_plots"

NUMERIC_FIELDS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
]


def numeric_summary(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    rows = []
    for field in fields:
        values = pd.to_numeric(df[field], errors="coerce").dropna()
        rows.append(
            {
                "field": field,
                "non_missing_count": len(values),
                "missing_count": len(df) - len(values),
                "min": values.min(),
                "p01": values.quantile(0.01),
                "p05": values.quantile(0.05),
                "p25": values.quantile(0.25),
                "mean": values.mean(),
                "median_p50": values.median(),
                "p75": values.quantile(0.75),
                "p95": values.quantile(0.95),
                "p99": values.quantile(0.99),
                "max": values.max(),
                "standard_deviation": values.std(),
            }
        )
    return pd.DataFrame(rows).round(2)


def outlier_summary(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Flag potential extremes with the standard 1.5*IQR rule."""
    rows = []
    for field in fields:
        values = pd.to_numeric(df[field], errors="coerce").dropna()
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        low_count = int((values < lower).sum())
        high_count = int((values > upper).sum())
        rows.append(
            {
                "field": field,
                "iqr_lower_bound": lower,
                "iqr_upper_bound": upper,
                "below_lower_bound": low_count,
                "above_upper_bound": high_count,
                "total_potential_outliers": low_count + high_count,
                "potential_outlier_percent":
                    ((low_count + high_count) / len(values) * 100)
                    if len(values)
                    else 0,
            }
        )
    return pd.DataFrame(rows).round(2)


def save_plots(df: pd.DataFrame, fields: list[str]) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    for field in fields:
        values = pd.to_numeric(df[field], errors="coerce").dropna()
        if values.empty:
            continue

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(values, bins=50, color="#4472C4", edgecolor="white")
        ax.set_title(f"Distribution of {field}")
        ax.set_xlabel(field)
        ax.set_ylabel("Number of records")
        ax.grid(axis="y", alpha=0.2)
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / f"{field}_histogram.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 3.5))
        ax.boxplot(values, vert=False, showfliers=True)
        ax.set_title(f"Boxplot of {field}")
        ax.set_xlabel(field)
        ax.grid(axis="x", alpha=0.2)
        fig.tight_layout()
        fig.savefig(PLOTS_DIR / f"{field}_boxplot.png", dpi=150)
        plt.close(fig)


def create_eda_answers(df: pd.DataFrame) -> str:
    lines = ["Weeks 2-3 Foundational EDA Answers", "=" * 42]

    if "PropertyType" in df.columns:
        counts = df["PropertyType"].value_counts(dropna=False)
        lines.append("\nProperty types in the filtered sold dataset:")
        for value, count in counts.items():
            lines.append(f"  {value}: {count:,} ({count / len(df) * 100:.2f}%)")

    if "ClosePrice" in df.columns:
        price = pd.to_numeric(df["ClosePrice"], errors="coerce")
        lines.append(f"\nAverage close price: ${price.mean():,.2f}")
        lines.append(f"Median close price:  ${price.median():,.2f}")

    if "DaysOnMarket" in df.columns:
        dom = pd.to_numeric(df["DaysOnMarket"], errors="coerce")
        lines.append(f"\nAverage Days on Market: {dom.mean():.2f}")
        lines.append(f"Median Days on Market:  {dom.median():.2f}")
        lines.append(f"95th percentile DOM:    {dom.quantile(0.95):.2f}")

    if {"ClosePrice", "ListPrice"}.issubset(df.columns):
        close = pd.to_numeric(df["ClosePrice"], errors="coerce")
        listed = pd.to_numeric(df["ListPrice"], errors="coerce")
        valid = close.notna() & listed.notna() & (listed > 0)
        comparison = close[valid] - listed[valid]
        lines.append("\nSale price compared with list price (valid price rows):")
        lines.append(f"  Above list: {(comparison > 0).mean() * 100:.2f}%")
        lines.append(f"  At list:    {(comparison == 0).mean() * 100:.2f}%")
        lines.append(f"  Below list: {(comparison < 0).mean() * 100:.2f}%")

    if {"ListingContractDate", "CloseDate"}.issubset(df.columns):
        listing_date = pd.to_datetime(df["ListingContractDate"], errors="coerce")
        close_date = pd.to_datetime(df["CloseDate"], errors="coerce")
        invalid = int((close_date < listing_date).sum())
        lines.append(f"\nClose date before listing date: {invalid:,} records")

    county_field = next(
        (name for name in ["CountyOrParish", "County"] if name in df.columns),
        None,
    )
    if county_field and "ClosePrice" in df.columns:
        county_data = df[[county_field, "ClosePrice"]].copy()
        county_data["ClosePrice"] = pd.to_numeric(
            county_data["ClosePrice"], errors="coerce"
        )
        county_summary = (
            county_data.dropna()
            .groupby(county_field)["ClosePrice"]
            .agg(transaction_count="count", median_close_price="median")
        )
        # Exclude counties with very few observations from the comparison.
        county_summary = county_summary[county_summary["transaction_count"] >= 10]
        county_summary = county_summary.nlargest(10, "median_close_price")
        lines.append("\nTop counties by median close price (at least 10 sales):")
        for county, row in county_summary.iterrows():
            lines.append(
                f"  {county}: ${row['median_close_price']:,.2f} "
                f"({int(row['transaction_count']):,} sales)"
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    if not SOLD_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {SOLD_PATH}")

    print(f"Loading {SOLD_PATH}...")
    sold = pd.read_csv(SOLD_PATH, low_memory=False)
    print(f"Loaded {len(sold):,} rows and {len(sold.columns)} columns.")

    available = [field for field in NUMERIC_FIELDS if field in sold.columns]
    unavailable = [field for field in NUMERIC_FIELDS if field not in sold.columns]
    if not available:
        raise ValueError("None of the requested numeric fields were found.")

    print(f"Available numeric fields: {available}")
    if unavailable:
        print(f"Unavailable fields (skipped): {unavailable}")

    summary = numeric_summary(sold, available)
    outliers = outlier_summary(sold, available)
    summary.to_csv(SUMMARY_PATH, index=False)
    outliers.to_csv(OUTLIER_PATH, index=False)

    print("Creating histograms and boxplots...")
    save_plots(sold, available)

    answers = create_eda_answers(sold)
    EDA_ANSWERS_PATH.write_text(answers, encoding="utf-8")

    print("\nRequired three-field distribution summary:")
    required = summary[
        summary["field"].isin(["ClosePrice", "LivingArea", "DaysOnMarket"])
    ]
    print(required.to_string(index=False))

    print("\nWeek 3 numeric EDA completed.")
    print(f"Saved {SUMMARY_PATH}")
    print(f"Saved {OUTLIER_PATH}")
    print(f"Saved {EDA_ANSWERS_PATH}")
    print(f"Saved plots in {PLOTS_DIR}")


if __name__ == "__main__":
    main()
