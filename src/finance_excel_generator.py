from pathlib import Path
import re
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "data" / "templates" / "CAPEX_FLOW_Proposed_Finance_Register_Template.xlsx"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

REGISTER_COLUMNS = [
    "Merchant_Name", "Vendor_ID", "Project_Code", "Project_Name", "Department",
    "Cost_Centre", "Financial_Year", "PO_Number", "PO_Line_No", "PO_Date",
    "Item_Description", "Spend_Category", "Quantity", "PO_Line_Total_INR",
    "Approval_Status", "Receipt_Status", "Invoice_Count", "Invoice_Amount_INR",
    "Received_Quantity", "Invoice_Match_Status", "Approved_Budget_INR",
    "Revised_Budget_Adjustment_INR", "Revised_Budget_INR",
    "Project_Approved_Commitments_INR", "Merchant_Approved_Commitment_INR",
    "Project_Remaining_Budget_INR", "Budget_Utilization_Pct", "Invoice_Variance_INR",
    "Uninvoiced_PO_Value_INR", "Review_Flag",
]
PROJECT_COLUMNS = [
    "Project_Code", "Project_Name", "Financial_Year", "Approved_Budget_INR",
    "Budget_Adjustment_INR", "Revised_Budget_INR",
    "Project_Approved_Commitments_INR", "Selected_Merchant_Commitment_INR",
    "Selected_Merchant_PO_Value_INR", "Selected_Merchant_Invoice_Value_INR",
    "Project_Remaining_Budget_INR", "Budget_Utilization_Pct",
]
RECON_COLUMNS = [
    "PO_Number", "PO_Line_No", "Project_Code", "Financial_Year",
    "PO_Line_Total_INR", "Invoice_Amount_INR", "Invoice_Variance_INR",
    "Approved_Budget_INR", "Revised_Budget_INR",
    "Project_Approved_Commitments_INR", "Project_Remaining_Budget_INR",
    "Review_Flag", "PO_Invoice_Check", "Budget_Check",
]


def _excel_value(value):
    if value is None:
        return None
    if pd.api.types.is_scalar(value) and pd.isna(value):
        return None
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (ValueError, AttributeError):
            return value
    return value


def _write_dataframe(ws, df, expected_columns):
    missing = [column for column in expected_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Output dataset is missing columns: {missing}")
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
        for cell in row:
            cell.value = None
    for row_idx, row in enumerate(df[expected_columns].itertuples(index=False, name=None), 5):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row_idx, col_idx).value = _excel_value(value)
    ws.auto_filter.ref = f"A4:{get_column_letter(len(expected_columns))}{len(df) + 4}"
    ws.freeze_panes = "A5"
    headers = {str(ws.cell(4, c).value): c for c in range(1, len(expected_columns) + 1)}
    currency_names = {
        "PO_Line_Total_INR", "Invoice_Amount_INR", "Approved_Budget_INR",
        "Revised_Budget_Adjustment_INR", "Revised_Budget_INR",
        "Project_Approved_Commitments_INR", "Merchant_Approved_Commitment_INR",
        "Project_Remaining_Budget_INR", "Invoice_Variance_INR",
        "Uninvoiced_PO_Value_INR", "Budget_Adjustment_INR",
        "Selected_Merchant_Commitment_INR", "Selected_Merchant_PO_Value_INR",
        "Selected_Merchant_Invoice_Value_INR",
    }
    for name, col in headers.items():
        if name in currency_names:
            for row in range(5, len(df) + 5):
                ws.cell(row, col).number_format = '"₹"#,##0.00;[Red]-"₹"#,##0.00'
        elif name == "Budget_Utilization_Pct":
            for row in range(5, len(df) + 5):
                ws.cell(row, col).number_format = '0.0"%"'


def generate_finance_register_excel(
    finance_result,
    merchant_name,
    template_path=DEFAULT_TEMPLATE,
    output_dir=DEFAULT_OUTPUT_DIR,
):
    """Populate a separate finance workbook; never modify the SOP input."""
    template_path = Path(template_path)
    output_dir = Path(output_dir)
    if not template_path.exists():
        raise FileNotFoundError(f"Finance register template not found: {template_path}")
    workbook = load_workbook(template_path)
    required_sheets = ["CAPEX Register", "Project Summary", "Reconciliation", "Read Me & Assumptions"]
    missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheetnames]
    if missing_sheets:
        raise ValueError(f"Finance template missing worksheets: {missing_sheets}")

    _write_dataframe(workbook["CAPEX Register"], finance_result["records"], REGISTER_COLUMNS)
    _write_dataframe(workbook["Project Summary"], finance_result["project_summary"], PROJECT_COLUMNS)
    _write_dataframe(workbook["Reconciliation"], finance_result["reconciliation"], RECON_COLUMNS)

    readme = workbook["Read Me & Assumptions"]
    context = [
        ("Generated for merchant", str(merchant_name)),
        ("Generated at", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("PO lines in report", int(len(finance_result["records"]))),
        ("Report status", "Synthetic POC — Finance review required"),
    ]
    for offset, (label, value) in enumerate(context, 18):
        readme.cell(offset, 1, label)
        readme.cell(offset, 2, value)
        readme.cell(offset, 1).font = Font(bold=True, color="FFFFFF")
        readme.cell(offset, 1).fill = PatternFill("solid", fgColor="315B91")
        readme.cell(offset, 2).alignment = Alignment(wrap_text=True)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(merchant_name)).strip("_") or "merchant"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CAPEX_Finance_Register_{safe_name}.xlsx"
    workbook.save(output_path)
    return output_path
