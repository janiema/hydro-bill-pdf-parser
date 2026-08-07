import os
import pandas as pd


def get_majority_month(row, from_col, to_col):
    """Calculates the month with the highest number of billing days."""
    start = pd.to_datetime(row[from_col], errors="coerce")
    end = pd.to_datetime(row[to_col], errors="coerce")

    if pd.isna(start) or pd.isna(end):
        return ""

    # Generate daily date range for the billing period
    date_range = pd.date_range(start=start, end=end)

    # Return the month name and year (e.g., 'June 2026') with the most days
    return date_range.strftime("%B %Y").value_counts().idxmax()


def clean_to_numeric(series):
    """Helper to convert currency strings/floats safely into numeric floats."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    ).fillna(0)


# 1. File path configuration
INPUT_FILE = r"T:\Corporate Services\Site Redevelopment\Energy Management\Uitility Billing Documents\Natural Gas\Utility Bills\06-Aug-26.xlsx"

input_dir = os.path.dirname(INPUT_FILE)
OUTPUT_FILE = os.path.join(input_dir, "E-block_NG_summary.xlsx")

# 2. Extract target columns: E, F, G, H, J, AA
TARGET_COLUMNS = "E,F,G,H,J,AA"
df = pd.read_excel(INPUT_FILE, usecols=TARGET_COLUMNS)

# 3. Reference columns by position index in df
from_col = df.columns[0]  # Excel E (Billed From)
to_col = df.columns[1]  # Excel F (Billed To)
consump_col = df.columns[4]  # Excel J (Consumption M3)
col_aa = df.columns[5]  # Excel AA (Total Charges, includes HST)

# 4. Rename Column AA header to "Total NG Charges + HST"
df.rename(columns={col_aa: "Total NG Charges + HST"}, inplace=True)
total_charges_col = "Total NG Charges + HST"

# 5. Calculate majority month for every row
billing_months = df.apply(
    lambda row: get_majority_month(row, from_col, to_col), axis=1
)
df.insert(0, "Billing Month", billing_months)

# 6. Clean numeric columns and calculate $/m3 (Column AA / Column J)
total_charges = clean_to_numeric(df[total_charges_col])
consumption = clean_to_numeric(df[consump_col])

# Compute unit rate (Column AA / Column J)
cost_per_m3 = total_charges / consumption

df["$/m3"] = cost_per_m3.apply(
    lambda x: f"${x:.4f}" if pd.notna(x) and x > 0 else "N/A"
)

# 7. Save back to the T: drive folder
df.to_excel(OUTPUT_FILE, index=False)

print(f"File updated and saved to: {OUTPUT_FILE}")