# mls-analytics
IDX Exchange Data Analyst Internship – MLS Analytics & Tableau Dashboard Program

# IDX Exchange – MLS Analytics Internship

A 12-week data analyst internship program analyzing real MLS (Multiple Listing Service) 
transaction data from the CoreLogic Trestle API to produce housing market insights and 
interactive Tableau dashboards.

## Project Overview

This project builds a full analytics pipeline:
1. Extract monthly MLS listing and sold transaction data
2. Clean and validate the dataset
3. Engineer key housing market metrics
4. Visualize findings in Tableau Public dashboards

## Tools & Technologies

- **Python** (Pandas) – data extraction, cleaning, and feature engineering
- **Tableau Public** – interactive dashboard development and publishing
- **GitHub** – version control and weekly progress tracking

## Repository Contents

```text
mls-analytics/
├── README.md
├── .gitignore
└── py/
    ├── week0_test.py
    ├── week1.py
    ├── week1_merge.py
    ├── week2_data_audit.py
    ├── week2_clean_columns.py
    ├── week3_numeric_eda.py
    ├── week3_mortgage_rate_enrichment.py
    ├── week4_5_data_cleaning.py
    ├── week6_feature_engineering.py
    ├── week7_outlier_detection.py
    └── week8_tableau_data_preparation.py
```

> Raw MLS files, processed datasets, validation reports, and plots remain local and are excluded from GitHub for confidentiality.

## How to Run

The scripts are designed to run from the local internship project folder:

```bash
cd /Users/tq/Desktop/da54/Files
python3 py/<script_name>.py
```

Each phase uses the locally generated outputs from the previous phase. Raw and processed MLS datasets are not included in this public repository.

## Weekly Progress

### Week 0 – Setup and Data Orientation
- Set up Python and VS Code environment.
- Verified that local MLS CSV files can be loaded with Pandas.
- Reviewed available listing and sold dataset fields.

### Week 1 – Monthly Dataset Aggregation
- Combined monthly CRMLS Listing files from January 2024 through May 2026.
- Selected one Sold file per month, preferring `_filled` files when available.
- Filtered both Listings and Sold datasets to `PropertyType == "Residential"`.
- Saved combined Residential datasets locally in the `processed/` folder.
- Raw and processed CSV files are excluded from GitHub for confidentiality.

### Week 2 – Data Audit and Column Cleaning
- Audited combined Residential Listing and Sold datasets for missing values.
- Generated missingness reports for both datasets.
- Dropped columns with more than 90% missing values based on project guidance.
- Saved cleaned Week 2 datasets in the `processed/` folder.
- Cleaned Listings dataset: 591,979 rows and 72 columns.
- Cleaned Sold dataset: 430,428 rows and 70 columns.
- Reviewed dropped columns and confirmed that key size fields such as `LivingArea`, `MLSAreaMajor`, `LotSizeAcres`, `LotSizeArea`, and `LotSizeSquareFeet` were retained.
- Raw and processed CSV files remain excluded from GitHub for confidentiality.

### Week 3 – Numeric EDA and Mortgage Rate Enrichment

- Conducted numeric exploratory data analysis on the cleaned Residential Listing and Sold datasets.
- Generated numeric summary reports and plots, saved locally in the `processed/` folder.
- Retrieved weekly 30-year fixed mortgage rates from FRED and calculated monthly averages.
- Merged mortgage rates with Listings using `ListingContractDate` and Sold records using `CloseDate`.
- Validated that Listings retained 591,979 rows before and after the merge.
- Validated that Sold retained 430,428 rows before and after the merge.
- Confirmed that there were no invalid or missing dates and no unmatched mortgage rates.
- Confirmed mortgage-rate coverage from January 2024 through May 2026, with every property record receiving a rate.
- Added `py/week3_numeric_eda.py` and `py/week3_mortgage_rate_enrichment.py` to the repository.
- Large processed and enriched CSV files remain excluded from GitHub for confidentiality.

### Weeks 4–5 – Data Cleaning and Preparation

- Converted required transaction date fields to datetime format.
- Confirmed that numeric analysis fields were properly typed.
- Consolidated and removed 11 fully redundant `.1` columns from the Listings dataset.
- Confirmed that the redundant columns contained no unique or conflicting values.
- Flagged invalid price, living-area, days-on-market, bedroom, and bathroom values.
- Replaced invalid numeric values with missing values while retaining the original records.
- Added date-consistency flags for invalid listing, contract, and closing timelines.
- Added geographic quality flags for missing, zero, positive-longitude, and implausible California coordinates.
- Preserved all 591,979 Listings rows and 430,428 Sold rows.
- Saved cleaned datasets and validation reports locally in the `processed/` folder.
- Added `py/week4_5_data_cleaning.py` to the repository.
- Large processed CSV files remain excluded from GitHub for confidentiality.

### Week 6 – Feature Engineering and Market Metrics

- Engineered `PriceRatio` and `CloseToOriginalListRatio` using `ClosePrice / OriginalListPrice`.
- Calculated `PricePerSqFt` using `ClosePrice / LivingArea`.
- Retained `DaysOnMarket` as the raw time-to-sell measure.
- Derived `Year`, `Month`, and `YrMo` from `CloseDate`.
- Calculated listing-to-contract and contract-to-close durations.
- Flagged negative date intervals and replaced invalid engineered durations with missing values while retaining the original records.
- Generated segmented summaries by property type, property subtype, county, MLS area, listing office, and buyer office.
- Preserved all 430,428 Sold records before and after feature engineering.
- Identified extreme positive values for systematic outlier analysis in Week 7 rather than applying arbitrary cutoffs.
- Saved the engineered dataset, sample output, feature summary, and segment summaries locally in the `processed/` folder.
- Added `py/week6_feature_engineering.py` to the repository.
- Large processed CSV files remain excluded from GitHub for confidentiality.

### Week 7 – Outlier Detection and Data Quality Validation

- Applied the standard 1.5 × IQR method to `ClosePrice`, `LivingArea`, and `DaysOnMarket`.
- Calculated Q1, median, Q3, IQR, lower and upper bounds, selected percentiles, and field-level outlier counts.
- Added separate Boolean outlier flags for each field and a combined exclusion flag.
- Reused the established business-rule flags from Weeks 4–5 while ensuring that missing values alone were not classified as outliers.
- Preserved all 430,428 Sold records in the full flagged dataset.
- Created a filtered analysis dataset containing 362,646 records after excluding 67,782 records, or 15.75% of the full dataset.
- Observed median changes from $825,000 to $785,000 for `ClosePrice`, 1,644 to 1,570 square feet for `LivingArea`, and 18 to 16 days for `DaysOnMarket`.
- Retained excluded observations in the flagged dataset because statistical outliers may represent legitimate transactions rather than data errors.
- Saved the flagged dataset, filtered dataset, IQR threshold report, and before-and-after comparison reports locally in the `processed/` folder.
- Added `py/week7_outlier_detection.py` to the repository.
- Large processed CSV files remain excluded from GitHub for confidentiality.

### Week 8 – Tableau Data Preparation and Market Dashboard Development

- Created a unified, long-format Tableau event table combining new-listing and closed-sale activity.
- Generated 591,979 new-listing event rows using `ListingContractDate`.
- Generated 362,646 closed-sale event rows using `CloseDate`.
- Combined 954,625 total market-event rows covering January 2024 through May 2026.
- Derived standardized event date, month, year, and year-month fields for monthly analysis.
- Standardized city, county, ZIP code, and property-subtype dimensions so the same filters could be applied across all Tableau worksheets.
- Confirmed that all required dashboard filter fields were at least 99.77% populated.
- Identified implausible `CloseToOriginalListRatio` values caused by placeholder `OriginalListPrice` entries.
- Set 1,517 ratios outside the plausible 0.50–1.50 range to missing for ratio analysis without removing their closed-sale records from other measures.
- Retained 360,582 valid close-to-original-list ratios, representing 99.43% of closed-sale events.
- Built five monthly Tableau worksheets for new listings, closed sales, median close price, average days on market, and average close-to-original-list ratio.
- Created the `Market Analysis` dashboard with shared city, county, ZIP code, and property-subtype filters.
- Verified that all five charts update correctly when the shared geographic filters are changed.
- Saved the Tableau packaged workbook locally as `tableau/market_analysis.twbx`.
- Saved the Tableau-ready dataset and validation reports locally in the `processed/` folder.
- Added `py/week8_tableau_data_preparation.py` to the repository.
- The packaged workbook and processed MLS datasets remain local and are excluded from GitHub for confidentiality.

## Final Deliverables

- Tableau dashboards published to [Tableau Public](#) *(link to be added)*
- 1-page Market Intelligence Report
- 5-minute live presentation
