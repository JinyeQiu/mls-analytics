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

| File | Description |
|------|-------------|
| `crmls_listed.py` | Pulls and updates the listings dataset (CSV) |
| `crmls_sold.py` | Pulls and updates the sold transactions dataset (CSV) |

> Note: Raw CSV data files are not included in this repository.

## How to Run

1. Make sure Python and Pandas are installed:
2. Run the listings script:
3. Run the sold script:

Each script appends new data to the existing CSV rather than creating a new file each week.

## Final Deliverables

- Tableau dashboards published to [Tableau Public](#) *(link to be added)*
- 1-page Market Intelligence Report
- 5-minute live presentation



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
