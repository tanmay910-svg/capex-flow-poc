
from pathlib import Path
import re
from copy import copy

import pandas as pd
from openpyxl import load_workbook

from src.excel_reader import read_capex_workbook
from src.merchant_matcher import search_merchant
from src.capex_processor import process_merchant_capex
from openpyxl.cell.cell import MergedCell
from src.config_loader import load_column_mapping
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TEMPLATE = (
    PROJECT_ROOT
    / "data"
    / "input"
    / "CAPEX_POC_Synthetic_Data_Pack.xlsx"
)

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

TEMPLATE_SHEET = "CAPEX_Output_Template"
HEADER_ROW = 4
FIRST_DATA_ROW = 5

# Explicit mapping between template columns and processing-engine fields.
COLUMN_MAPPING = load_column_mapping()["output_mapping"]

def clean_excel_value(value):
    """Convert Pandas and NumPy values into Excel-compatible values."""

    if value is None:
        return None

    if not pd.api.types.is_scalar(value):
        return str(value)

    if pd.isna(value):
        return None

    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass

    return value


def copy_row_formatting(worksheet, source_row, target_row):
    """Copy cell formatting from the template's first data row."""

    for column in range(1, worksheet.max_column + 1):
        source = worksheet.cell(source_row, column)
        target = worksheet.cell(target_row, column)

        if source.has_style:
            target._style = copy(source._style)

        if source.number_format:
            target.number_format = source.number_format

        if source.alignment:
            target.alignment = copy(source.alignment)

        if source.protection:
            target.protection = copy(source.protection)

    source_dimension = worksheet.row_dimensions[source_row]
    target_dimension = worksheet.row_dimensions[target_row]

    if source_dimension.height is not None:
        target_dimension.height = source_dimension.height


def validate_template_headers(worksheet):
    """Check that the expected output columns exist in the template."""

    actual_headers = [
        worksheet.cell(HEADER_ROW, column).value
        for column in range(1, worksheet.max_column + 1)
    ]

    actual_headers = [
        str(header).strip() if header is not None else None
        for header in actual_headers
    ]

    missing_headers = [
        header
        for header in COLUMN_MAPPING
        if header not in actual_headers
    ]

    if missing_headers:
        raise ValueError(
            f"Template is missing required headers: {missing_headers}"
        )

    return actual_headers


def generate_capex_excel(
    processed_records,
    merchant_name,
    template_path=DEFAULT_TEMPLATE,
    output_dir=DEFAULT_OUTPUT_DIR,
):
    """
    Populate the generic CAPEX output template with processed records.

    The original input workbook is never modified.
    """

    if processed_records is None or processed_records.empty:
        raise ValueError("No processed records were provided.")

    template_path = Path(template_path)
    output_dir = Path(output_dir)

    if not template_path.exists():
        raise FileNotFoundError(
            f"CAPEX template not found: {template_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    workbook = load_workbook(template_path)

    if TEMPLATE_SHEET not in workbook.sheetnames:
        raise ValueError(
            f"Worksheet '{TEMPLATE_SHEET}' not found in template."
        )

    worksheet = workbook[TEMPLATE_SHEET]

    headers = validate_template_headers(worksheet)

    # Map each template header to its Excel column number.
    header_positions = {
        header: index + 1
        for index, header in enumerate(headers)
        if header is not None
    }

    # Confirm that the processing engine contains every required field.
    required_source_fields = [
        source
        for source in COLUMN_MAPPING.values()
        if source is not None
    ]

    missing_source_fields = [
        field
        for field in required_source_fields
        if field not in processed_records.columns
    ]

    if missing_source_fields:
        raise ValueError(
            "Processing output is missing fields: "
            f"{missing_source_fields}"
        )

    record_count = len(processed_records)

    # Preserve the existing template layout and clear old sample values.
    last_existing_row = worksheet.max_row

    for row in worksheet.iter_rows(
    min_row=FIRST_DATA_ROW,
    max_row=last_existing_row,
    min_col=1,
    max_col=worksheet.max_column,
):
     for cell in row:
        if not isinstance(cell, MergedCell):
            cell.value = None

    # Write processed records into the template.
    for record_index, (_, record) in enumerate(
        processed_records.iterrows()
    ):
        excel_row = FIRST_DATA_ROW + record_index

        # Extend formatting if there are more records than template rows.
        if excel_row > last_existing_row:
            copy_row_formatting(
                worksheet,
                FIRST_DATA_ROW,
                excel_row,
            )

        for template_header, source_field in COLUMN_MAPPING.items():
            column_number = header_positions[template_header]

            if source_field is None:
                value = None
            else:
                value = record[source_field]

            worksheet.cell(
                row=excel_row,
                column=column_number,
            ).value = clean_excel_value(value)

    last_data_row = FIRST_DATA_ROW + record_count - 1

    # Make the generated report easier to navigate.
    worksheet.freeze_panes = f"A{FIRST_DATA_ROW}"
    worksheet.auto_filter.ref = (
        f"A{HEADER_ROW}:R{last_data_row}"
    )

    # Create a safe filename from the merchant name.
    safe_merchant_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(merchant_name).strip(),
    ).strip("_")

    if not safe_merchant_name:
        safe_merchant_name = "Merchant"

    output_path = (
        output_dir
        / f"CAPEX_Output_{safe_merchant_name}.xlsx"
    )

    workbook.save(output_path)
    workbook.close()

    print("\n========== EXCEL GENERATION SUMMARY ==========")
    print(f"Merchant: {merchant_name}")
    print(f"Records exported: {record_count}")
    print(f"Template used: {template_path.name}")
    print(f"Output file: {output_path}")

    return output_path


if __name__ == "__main__":

    # Load the synthetic workbook.
    workbook_data = read_capex_workbook()

    # Find the test merchant.
    merchant_result = search_merchant(
        workbook_data,
        "ABC Technologies",
    )

    if merchant_result["merchant"]["status"] != "FOUND":
        raise ValueError("Test merchant could not be identified.")

    # Process the merchant's purchase orders.
    processing_result = process_merchant_capex(
        workbook_data,
        merchant_result,
    )

    # Generate the final Excel report.
    generate_capex_excel(
        processed_records=processing_result["records"],
        merchant_name=merchant_result["merchant"]["merchant_name"],
    )
