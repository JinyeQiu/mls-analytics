from pathlib import Path
import pandas as pd

# Locate folders
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

# Local CSV file path
# Raw CSV files are not uploaded to GitHub.
csv_file = project_root / "csv" / "CRMLSListing202401.csv"

print("CSV path:")
print(csv_file)

# Load one sample MLS listing file to verify Python/Pandas setup
df = pd.read_csv(csv_file, low_memory=False)

print("\nFirst five rows:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print(f"\nNumber of columns: {len(df.columns)}")
for i, col in enumerate(df.columns, start=1):
    print(f"{i:3}. {col}")