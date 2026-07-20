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
    └── week4_5_data_cleaning.py
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

## Final Deliverables

- Tableau dashboards published to [Tableau Public](#) *(link to be added)*
- 1-page Market Intelligence Report
- 5-minute live presentation
