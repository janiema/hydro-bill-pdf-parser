from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import pdfplumber


def parse_toronto_hydro_bill(pdf_path: Path) -> dict[str, str]:
    """Precision parser tailored for Toronto Hydro commercial/general service bills."""
    data = {
        "File Name": pdf_path.name,
        "Reporting Month": "Unknown",
        "Total Charges + HST": "Not found",
        "Meter Number": "Not found",
        "Meter Reading Period": "Not found",
        "Number of Days": "Not found",
        "Adjusted kWh Used": "Not found",
        "Adj kW": "Not found",
    }

    with pdfplumber.open(pdf_path) as pdf:
        page1_text = pdf.pages[0].extract_text() or ""
        lines = page1_text.split("\n")

        for i, line in enumerate(lines):
            # 1. Total Charges + HST (Flexible pattern matching)
            # Searches for common labels like "Total Charges", "Total Amount Due", "Total New Charges"
            if data["Total Charges + HST"] == "Not found":
                if re.search(r"total\s+(charges|amount|new\s+charges)", line, re.IGNORECASE):
                    m = re.search(r"\$\s*([\d,]+\.\d{2})", line)
                    if m:
                        data["Total Charges + HST"] = f"${m.group(1)}"

            # 2. Meter Details
            if "Meter Reading Period" in line and i + 1 < len(lines):
                val_line = lines[i + 1]
                pattern = (
                    r"^(\d+)\s+"
                    r"([A-Za-z]{3}\s+\d{1,2}\s+\d{4}\s+TO\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{4})\s+"
                    r"(\d+)\s+"
                    r"\d+\s+[\d\.]+\s+[\d\.]+\s+"
                    r"([\d\.]+)"
                )
                m = re.search(pattern, val_line, re.IGNORECASE)
                if m:
                    data["Meter Number"] = m.group(1)
                    data["Meter Reading Period"] = m.group(2)
                    data["Number of Days"] = m.group(3)
                    data["Adjusted kWh Used"] = m.group(4)

            # 3. Adj kW
            if "Adj. kW" in line or "Adj kW" in line:
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        target_line = lines[i + offset]
                        floats = re.findall(r"\b\d+\.\d{3}\b", target_line)
                        if len(floats) >= 2:
                            data["Adj kW"] = floats[1]
                            break

        # Fallback for Total Charges: If not found on page 1, search the entire page for any dollar figure near "Total"
        if data["Total Charges + HST"] == "Not found":
            fallback_match = re.search(r"(?:Total|Amount Due|New Charges)[^\$\n]*\$\s*([\d,]+\.\d{2})", page1_text, re.IGNORECASE)
            if fallback_match:
                data["Total Charges + HST"] = f"${fallback_match.group(1)}"

    # Calculate Reporting Month based on the midpoint (majority of days) of the reading period
    if data["Meter Reading Period"] != "Not found":
        try:
            parts = data["Meter Reading Period"].split(" TO ")
            d_start = datetime.strptime(parts[0].strip(), "%b %d %Y")
            d_end = datetime.strptime(parts[1].strip(), "%b %d %Y")

            midpoint = d_start + (d_end - d_start) / 2
            data["Reporting Month"] = midpoint.strftime("%B %Y")
        except (IndexError, ValueError):
            pass

    # Fallback to filename if reading period couldn't be parsed
    if data["Reporting Month"] == "Unknown":
        filename_parts = pdf_path.stem.split("_")
        if len(filename_parts) >= 4:
            try:
                dt = datetime.strptime(
                    f"{filename_parts[2]}-{filename_parts[3]}", "%Y-%m"
                )
                data["Reporting Month"] = dt.strftime("%B %Y")
            except ValueError:
                pass

    return data


def main() -> None:
    folder_path = Path(
        r"C:\Users\Janie_Ma\OneDrive - CAMH\Documents\CAMH Code\.venv\Hydro Utility Bills\E Block"
    )

    if not folder_path.exists():
        print(f"Error: Folder does not exist at {folder_path}")
        return

    pdf_files = sorted(folder_path.glob("TH_*.pdf"))

    if not pdf_files:
        print(f"No matching PDF bills found in {folder_path}")
        return

    print(f"Found {len(pdf_files)} bills. Processing...\n")

    results = []
    for pdf in pdf_files:
        print(f"Parsing: {pdf.name}...")
        results.append(parse_toronto_hydro_bill(pdf))

    df = pd.DataFrame(results)

    output_excel_path = folder_path / "E_block_hydro_summary.xlsx"
    df.to_excel(output_excel_path, index=False)

    print("\nAll bills parsed.")
    print(f"Excel file saved at: {output_excel_path}")


if __name__ == "__main__":
    main()p