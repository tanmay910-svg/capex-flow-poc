
"""
CAPEX Automation POC
Module: Excel Reader

Reads CAPEX workbooks from either:
1. A default local synthetic workbook.
2. A user-uploaded Excel workbook.
"""

from pathlib import Path
import logging

import pandas as pd

from src.config_loader import load_column_mapping


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "input"
    / "CAPEX_POC_Synthetic_Data_Pack.xlsx"
)


# Load workbook configuration
COLUMN_CONFIG = load_column_mapping()

SHEET_MAPPING = COLUMN_CONFIG["sheets"]

REQUIRED_SHEETS = [
    SHEET_MAPPING["sop"],
    SHEET_MAPPING["vendors"],
    SHEET_MAPPING["projects"],
    SHEET_MAPPING["budget"],
    SHEET_MAPPING["invoice_receipt"],
]

# JSON uses Excel row numbering; Pandas uses zero-based header indexing.
HEADER_ROW = int(COLUMN_CONFIG["header_row"]) - 1


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def read_capex_workbook(file_path=None):
    """
    Read all required worksheets from a CAPEX workbook.

    Accepts:
        - A local Excel file path.
        - A Streamlit UploadedFile object.
        - None, to use the default synthetic workbook.

    Returns:
        dict: Dictionary containing DataFrames for each sheet.
    """

    if file_path is None:
        file_source = DEFAULT_DATA_FILE
        source_name = DEFAULT_DATA_FILE.name

    elif isinstance(file_path, (str, Path)):
        file_source = Path(file_path)
        source_name = file_source.name

        if not file_source.exists():
            raise FileNotFoundError(
                f"CAPEX workbook not found: {file_source}"
            )

    else:
        # Handle uploaded file objects such as Streamlit UploadedFile.
        file_source = file_path
        source_name = getattr(
            file_path,
            "name",
            "uploaded_workbook.xlsx"
        )

        # Reset the upload stream before reading.
        if hasattr(file_source, "seek"):
            file_source.seek(0)

    logger.info("Reading CAPEX workbook: %s", source_name)

    try:
        excel_file = pd.ExcelFile(file_source)

    except Exception as error:
        raise ValueError(
            f"Unable to open Excel workbook: {error}"
        ) from error

    try:
        available_sheets = excel_file.sheet_names

        missing_sheets = [
            sheet
            for sheet in REQUIRED_SHEETS
            if sheet not in available_sheets
        ]

        if missing_sheets:
            raise ValueError(
                f"Missing required worksheets: {missing_sheets}"
            )

        data = {}

        for sheet_name in REQUIRED_SHEETS:

            logger.info("Reading worksheet: %s", sheet_name)

            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                header=HEADER_ROW
            )

            # Clean column names.
            df.columns = (
                df.columns
                .astype(str)
                .str.strip()
            )

            # Remove completely empty rows.
            df = df.dropna(how="all")

            data[sheet_name] = df

            logger.info(
                "%s loaded successfully | Records: %s | Columns: %s",
                sheet_name,
                len(df),
                len(df.columns)
            )

        logger.info(
            "All required worksheets loaded successfully."
        )

        return data

    finally:
        excel_file.close()


def print_workbook_summary(data):
    """Display a summary of all loaded worksheets."""

    print("\n========== CAPEX WORKBOOK SUMMARY ==========\n")

    for sheet_name, df in data.items():

        print(f"Worksheet: {sheet_name}")
        print(f"Records: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        print("-" * 60)


if __name__ == "__main__":

    workbook_data = read_capex_workbook()

    print_workbook_summary(workbook_data)
