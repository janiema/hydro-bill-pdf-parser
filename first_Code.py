# /// script
# requires-python = ">=3.11"
# dependencies = [
#   pdfplumber
# ]
# ///

from __future__ import annotations

import re
from pathlib import Path
import pdfplumber


def parse_toronto_hydro_bill(pdf_path: Path) -> dict[str, str]:
    """Precision parser tailored for Toronto Hydro commercial/general service bills."""
    
    data = {
        "Amount Due": "Not found",
        "Meter Number": "Not found",
        "Meter Reading Period": "Not found",
        "Number of Days": "Not found",
        "Adjusted kWh Used": "Not found",
        "Adj kW": "Not found",
    }

    with pdfplumber.open(pdf_path) as pdf:
        # Extract text from Page 1 where usage and summary reside
        page1_text = pdf.pages[0].extract_text() or ""
        lines = page1_text.split("\n")

        for i, line in enumerate(lines):
            
            # 1. Amount Due
            if "Total Amount Due" in line or "Amount Due:" in line:
                m = re.search(r"\$\s*([\d,]+\.\d{2})", line)
                if m:
                    data["Amount Due"] = f"${m.group(1)}"

            # 2. Extract Meter #, Date Range, Days, and Adjusted kWh from line following table headers
            # Header line contains: "Meter Number Meter Reading Period of Days ... Adjusted kWh Used"
            if "Meter Reading Period" in line and i + 1 < len(lines):
                val_line = lines[i + 1]  # Line directly below header (P1-L53)
                
                # Regex matches: [Meter#] [DATE TO DATE] [Days] [Unit] [kWh Used] [Loss Factor] [Adjusted kWh]
                # Example: 507 MAR 23 2025 TO APR 23 2025 31 1 95196.936 1.0295 98005.246
                pattern = (
                    r"^(\d+)\s+"  # Meter Number (507)
                    r"([A-Za-z]{3}\s+\d{1,2}\s+\d{4}\s+TO\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{4})\s+"  # Date Range
                    r"(\d+)\s+"   # Days (31)
                    r"\d+\s+[\d\.]+\s+[\d\.]+\s+"  # Skip Unit Contained, kWh Used, Loss Factor
                    r"([\d\.]+)"  # Adjusted kWh Used (98005.246)
                )
                
                m = re.search(pattern, val_line, re.IGNORECASE)
                if m:
                    data["Meter Number"] = m.group(1)
                    data["Meter Reading Period"] = m.group(2)
                    data["Number of Days"] = m.group(3)
                    data["Adjusted kWh Used"] = m.group(4)

            # 3. Extract Adj kW
            # Line containing "Adj. kW" has values two lines below on Toronto Hydro bills (P1-L57)
            if "Adj. kW" in line or "Adj kW" in line:
                # Search surrounding lines (i+1 to i+3) for the row with demand floats (e.g., 167.184 172.756 ...)
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        target_line = lines[i + offset]
                        floats = re.findall(r"\b\d+\.\d{3}\b", target_line)
                        if len(floats) >= 2:
                            # In Toronto Hydro layout: [Peak kW] [Adj. Peak kW] ...
                            # 172.756 is the second float corresponding to Adj. Peak kW
                            data["Adj kW"] = floats[1]
                            break

    return data


def main() -> None:
    pdf_path = Path(r"C:\Users\Janie_Ma\OneDrive - CAMH\Documents\CAMH Code\.venv\Hydro Utility Bills\TH_4622301000_2025_05_01.pdf")

    if not pdf_path.exists():
        print(f"Error: Could not find file at:\n{pdf_path}")
        return

    extracted_data = parse_toronto_hydro_bill(pdf_path)

    print(f"PDF Path:{pdf_path}")
    for key, value in extracted_data.items():
        print(f"  {key:<22}: {value}")



if __name__ == "__main__":
    main()