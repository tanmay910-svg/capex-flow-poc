
"""
CAPEX Automation POC
Module: Data Validator

Validates workbook schemas, records, financial values,
and relationships between worksheets.
"""

import logging
import pandas as pd
from src.config_loader import load_validation_rules

logger = logging.getLogger(__name__)


VALIDATION_RULES = load_validation_rules()

REQUIRED_COLUMNS = {
    "SOP_Dump": VALIDATION_RULES["required_sop_columns"],
    "Vendor_Master": VALIDATION_RULES["required_vendor_columns"],
    "Project_Master": VALIDATION_RULES["required_project_columns"],
    "CAPEX_Budget": VALIDATION_RULES["required_budget_columns"],
    "Invoice_Receipt": VALIDATION_RULES["required_invoice_columns"]
}


def clean_text(value):
    """Clean either a Pandas Series or an individual value."""

    if isinstance(value, pd.Series):
        return value.astype("string").str.strip()

    if pd.isna(value):
        return ""

    return str(value).strip()


def add_issue(issues, severity, sheet, message, count=1):
    """Add a structured validation issue."""
    issues.append({
        "Severity": severity,
        "Sheet": sheet,
        "Issue": message,
        "Affected_Records": count
    })


def validate_required_columns(data, issues):
    """Check whether all required columns exist."""

    for sheet, required in REQUIRED_COLUMNS.items():

        if sheet not in data:
            add_issue(
                issues, "ERROR", sheet,
                "Required worksheet is missing."
            )
            continue

        actual_columns = set(data[sheet].columns)

        missing = [
            col for col in required
            if col not in actual_columns
        ]

        if missing:
            add_issue(
                issues,
                "ERROR",
                sheet,
                f"Missing columns: {missing}"
            )


def validate_empty_sheets(data, issues):
    """Check for empty required worksheets."""

    for sheet in REQUIRED_COLUMNS:

        if sheet not in data:
            continue

        if data[sheet].empty:
            add_issue(
                issues, "ERROR", sheet,
                "Worksheet contains no records."
            )


def validate_missing_values(data, issues):
    """Check essential fields for missing values."""

    required_fields = {
        "SOP_Dump": [
            "PO_Number", "PO_Line_No", "Vendor_ID",
            "Merchant_Name", "Project_Code",
            "Quantity", "Unit_Price_INR",
            "PO_Line_Total_INR"
        ],

        "Vendor_Master": [
            "Vendor_ID", "Merchant_Name"
        ],

        "Project_Master": [
            "Project_Code", "Project_Name"
        ],

        "CAPEX_Budget": [
            "Project_Code", "Financial_Year"
        ],

        "Invoice_Receipt": [
            "Invoice_Number", "PO_Number",
            "PO_Line_No", "Vendor_ID"
        ]
    }

    for sheet, columns in required_fields.items():

        if sheet not in data:
            continue

        df = data[sheet]

        for column in columns:

            if column not in df.columns:
                continue

            missing_count = int(df[column].isna().sum())

            if missing_count:
                add_issue(
                    issues, "ERROR", sheet,
                    f"Missing values in {column}",
                    missing_count
                )




def validate_duplicates(data, issues):
    """
    Check duplicate business identifiers using JSON configuration
    and detect suspicious repeated invoice-to-PO references.
    """

    duplicate_checks = VALIDATION_RULES["unique_keys"]

    # 1. Standard business identifier checks.
    for sheet, columns in duplicate_checks.items():

        if sheet not in data:
            continue

        df = data[sheet]

        if not all(col in df.columns for col in columns):
            continue

        duplicates = df.duplicated(
            subset=columns,
            keep=False
        )

        duplicate_count = int(duplicates.sum())

        if duplicate_count > 0:
            add_issue(
                issues,
                "ERROR",
                sheet,
                f"Duplicate business identifiers: {columns}",
                duplicate_count
            )

    # 2. Suspicious repeated invoice-to-PO references.
    if "Invoice_Receipt" in data:

        invoices = data["Invoice_Receipt"]

        reference_columns = [
            "Invoice_Number",
            "PO_Number",
            "PO_Line_No"
        ]

        if all(col in invoices.columns for col in reference_columns):

            repeated_references = invoices.duplicated(
                subset=reference_columns,
                keep=False
            )

            reference_count = int(repeated_references.sum())

            if reference_count > 0:
                add_issue(
                    issues,
                    "WARNING",
                    "Invoice_Receipt",
                    "Repeated invoice-to-PO line references require review",
                    reference_count
                )

    # --------------------------------------------------
    # 1. STANDARD BUSINESS IDENTIFIER CHECKS
    # --------------------------------------------------

    for sheet, columns in duplicate_checks.items():

        if sheet not in data:
            continue

        df = data[sheet]

        if not all(col in df.columns for col in columns):
            continue

        duplicates = df.duplicated(
            subset=columns,
            keep=False,
        )

        duplicate_count = int(duplicates.sum())

        if duplicate_count > 0:

            add_issue(
                issues,
                "ERROR",
                sheet,
                f"Duplicate business identifiers: {columns}",
                duplicate_count,
            )

    # --------------------------------------------------
    # 2. DUPLICATE INVOICE-TO-PO LINE REFERENCES
    # --------------------------------------------------

    if "Invoice_Receipt" in data:

        invoices = data["Invoice_Receipt"]

        reference_columns = [
            "Invoice_Number",
            "PO_Number",
            "PO_Line_No",
        ]

        if all(
            column in invoices.columns
            for column in reference_columns
        ):

            # A repeated invoice number against the same PO line
            # is suspicious and should be investigated.
            repeated_references = invoices.duplicated(
                subset=["Invoice_Number", "PO_Number", "PO_Line_No"],
                keep=False,
            )

            reference_count = int(
                repeated_references.sum()
            )

            if reference_count > 0:

                add_issue(
                    issues,
                    "WARNING",
                    "Invoice_Receipt",
                    "Repeated invoice-to-PO line references require review",
                    reference_count,
                )


def validate_numeric_values(data, issues):
    """Check numeric fields for invalid or negative values."""

    numeric_fields = {
        "SOP_Dump": [
            "Quantity", "Unit_Price_INR",
            "Discount_INR", "Tax_Amount_INR",
            "PO_Line_Total_INR"
        ],

        "CAPEX_Budget": [
            "Approved_Budget_INR",
            "Revised_Budget_Adjustment_INR"
        ],

        "Invoice_Receipt": [
            "Invoice_Amount_INR", "Received_Quantity"
        ]
    }

    for sheet, columns in numeric_fields.items():

        if sheet not in data:
            continue

        df = data[sheet]

        for column in columns:

            if column not in df.columns:
                continue

            values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            invalid = df[column].notna() & values.isna()

            if invalid.any():
                add_issue(
                    issues, "ERROR", sheet,
                    f"Non-numeric values in {column}",
                    int(invalid.sum())
                )

            negative = values < 0

            if negative.any():
                add_issue(
                    issues, "ERROR", sheet,
                    f"Negative values in {column}",
                    int(negative.sum())
                )

    # Quantity must be positive.
    if "SOP_Dump" in data and "Quantity" in data["SOP_Dump"]:
        qty = pd.to_numeric(
            data["SOP_Dump"]["Quantity"],
            errors="coerce"
        )

        invalid_qty = qty.notna() & (qty <= 0)

        if invalid_qty.any():
            add_issue(
                issues, "ERROR", "SOP_Dump",
                "Quantity must be greater than zero.",
                int(invalid_qty.sum())
            )


def validate_financial_calculations(data, issues):
    """Verify the synthetic PO line amount calculation."""

    if "SOP_Dump" not in data:
        return

    df = data["SOP_Dump"]

    required = [
        "Quantity", "Unit_Price_INR",
        "Discount_INR", "Tax_Amount_INR",
        "PO_Line_Total_INR"
    ]

    if not all(col in df.columns for col in required):
        return

    numeric = df[required].apply(
        pd.to_numeric, errors="coerce"
    )

    valid = numeric.notna().all(axis=1)

    taxable_value = (
        numeric["Quantity"] * numeric["Unit_Price_INR"]
        - numeric["Discount_INR"]
    )

    expected_total = taxable_value + numeric["Tax_Amount_INR"]

    mismatch = (
        valid
        & (taxable_value >= 0)
        & (
            (expected_total - numeric["PO_Line_Total_INR"]).abs()
            > 0.01
        )
    )

    if mismatch.any():
        add_issue(
            issues, "ERROR", "SOP_Dump",
            "PO line total does not match quantity, unit price, "
            "discount and tax calculation.",
            int(mismatch.sum())
        )


def validate_references(data, issues):
    """Validate relationships between workbook worksheets."""

    if not all(
        sheet in data
        for sheet in ["SOP_Dump", "Vendor_Master", "Project_Master"]
    ):
        return

    sop = data["SOP_Dump"]
    vendors = data["Vendor_Master"]
    projects = data["Project_Master"]

    if not all(
        col in sop.columns
        for col in ["Vendor_ID", "Project_Code"]
    ):
        return

    if "Vendor_ID" in vendors.columns:

        known_vendors = set(
            clean_text(vendors["Vendor_ID"]).dropna()
        )

        sop_vendors = clean_text(sop["Vendor_ID"])

        unknown = (
            sop_vendors.notna()
            & ~sop_vendors.isin(known_vendors)
        )

        if unknown.any():
            add_issue(
                issues, "ERROR", "SOP_Dump",
                "Unknown Vendor_ID references.",
                int(unknown.sum())
            )

    if "Project_Code" in projects.columns:

        known_projects = set(
            clean_text(projects["Project_Code"]).dropna()
        )

        sop_projects = clean_text(sop["Project_Code"])

        unknown = (
            sop_projects.notna()
            & ~sop_projects.isin(known_projects)
        )

        if unknown.any():
            add_issue(
                issues, "ERROR", "SOP_Dump",
                "Unknown Project_Code references.",
                int(unknown.sum())
            )

    # Verify vendor ID and merchant name consistency.
    if all(
        col in vendors.columns
        for col in ["Vendor_ID", "Merchant_Name"]
    ) and all(
        col in sop.columns
        for col in ["Vendor_ID", "Merchant_Name"]
    ):

        vendor_map = (
            vendors.dropna(subset=["Vendor_ID"])
            .assign(
                Vendor_ID=lambda x: clean_text(x["Vendor_ID"])
            )
            .drop_duplicates("Vendor_ID")
            .set_index("Vendor_ID")["Merchant_Name"]
            .astype("string").str.strip().str.casefold()
        )

        sop_ids = clean_text(sop["Vendor_ID"])
        sop_names = clean_text(sop["Merchant_Name"]).str.casefold()

        expected_names = sop_ids.map(vendor_map)

        mismatch = (
            expected_names.notna()
            & sop_names.notna()
            & (expected_names != sop_names)
        )

        if mismatch.any():
            add_issue(
                issues, "WARNING", "SOP_Dump",
                "Merchant name does not match Vendor Master.",
                int(mismatch.sum())
            )

    # Verify project code and project name consistency.
    if all(
        col in projects.columns
        for col in ["Project_Code", "Project_Name"]
    ) and all(
        col in sop.columns
        for col in ["Project_Code", "Project_Name"]
    ):

        project_map = (
            projects.dropna(subset=["Project_Code"])
            .assign(
                Project_Code=lambda x: clean_text(x["Project_Code"])
            )
            .drop_duplicates("Project_Code")
            .set_index("Project_Code")["Project_Name"]
            .astype("string").str.strip().str.casefold()
        )

        sop_codes = clean_text(sop["Project_Code"])
        sop_names = clean_text(sop["Project_Name"]).str.casefold()

        expected_names = sop_codes.map(project_map)

        mismatch = (
            expected_names.notna()
            & sop_names.notna()
            & (expected_names != sop_names)
        )

        if mismatch.any():
            add_issue(
                issues, "WARNING", "SOP_Dump",
                "Project name does not match Project Master.",
                int(mismatch.sum())
            )



def validate_invoice_references(data, issues):
    """
    Ensure invoice records reference existing PO lines
    and have matching vendor and merchant details.
    """

    if not all(
        sheet in data
        for sheet in ["SOP_Dump", "Invoice_Receipt"]
    ):
        return

    sop = data["SOP_Dump"]
    invoices = data["Invoice_Receipt"]

    key_columns = ["PO_Number", "PO_Line_No"]

    if not all(
        col in sop.columns and col in invoices.columns
        for col in key_columns
    ):
        return

    # Create a lookup of valid PO lines.
    sop_keys = set(
        zip(
            clean_text(sop["PO_Number"]),
            clean_text(sop["PO_Line_No"])
        )
    )

    invoice_keys = list(
        zip(
            clean_text(invoices["PO_Number"]),
            clean_text(invoices["PO_Line_No"])
        )
    )

    # Check whether invoice records reference valid PO lines.
    orphan_count = sum(
        key not in sop_keys
        for key in invoice_keys
    )

    if orphan_count:
        add_issue(
            issues,
            "ERROR",
            "Invoice_Receipt",
            "Invoice records reference nonexistent PO lines.",
            orphan_count
        )

    # Build a lookup for vendor and merchant details.
    sop_lookup = {}

    for _, row in sop.iterrows():
        key = (
            clean_text(row["PO_Number"]),
            clean_text(row["PO_Line_No"])
        )

        sop_lookup[key] = {
            "Vendor_ID": (
                clean_text(row["Vendor_ID"])
                if "Vendor_ID" in sop.columns else None
            ),
            "Merchant_Name": (
                clean_text(row["Merchant_Name"])
                if "Merchant_Name" in sop.columns else None
            )
        }

    # Check vendor and merchant consistency.
    vendor_mismatch_count = 0
    merchant_mismatch_count = 0

    for _, invoice in invoices.iterrows():

        key = (
            clean_text(invoice["PO_Number"]),
            clean_text(invoice["PO_Line_No"])
        )

        # Skip records whose PO line does not exist.
        if key not in sop_lookup:
            continue

        po_details = sop_lookup[key]

        if (
            "Vendor_ID" in invoices.columns
            and po_details["Vendor_ID"] is not None
            and clean_text(invoice["Vendor_ID"])
                != po_details["Vendor_ID"]
        ):
            vendor_mismatch_count += 1

        if (
            "Merchant_Name" in invoices.columns
            and po_details["Merchant_Name"] is not None
            and clean_text(invoice["Merchant_Name"])
                != po_details["Merchant_Name"]
        ):
            merchant_mismatch_count += 1

    if vendor_mismatch_count:
        add_issue(
            issues,
            "ERROR",
            "Invoice_Receipt",
            "Invoice Vendor_ID does not match the referenced PO vendor.",
            vendor_mismatch_count
        )

    if merchant_mismatch_count:
        add_issue(
            issues,
            "ERROR",
            "Invoice_Receipt",
            "Invoice Merchant_Name does not match the referenced PO merchant.",
            merchant_mismatch_count
        )


def validate_workbook(data):
    """
    Run all validation checks.

    Returns:
        Dictionary containing validation status,
        summary and issue details.
    """

    logger.info("Starting workbook validation...")

    issues = []

    validate_required_columns(data, issues)
    validate_empty_sheets(data, issues)

    # Run data-level checks only when the expected schema exists.
    schema_valid = all(
        sheet in data
        and all(
            col in data[sheet].columns
            for col in REQUIRED_COLUMNS[sheet]
        )
        for sheet in REQUIRED_COLUMNS
    )

    if schema_valid:
        validate_missing_values(data, issues)
        validate_duplicates(data, issues)
        validate_numeric_values(data, issues)
        validate_financial_calculations(data, issues)
        validate_references(data, issues)
        validate_invoice_references(data, issues)

    report = pd.DataFrame(
        issues,
        columns=[
            "Severity", "Sheet", "Issue", "Affected_Records"
        ]
    )

    errors = sum(
        issue["Severity"] == "ERROR"
        for issue in issues
    )

    warnings = sum(
        issue["Severity"] == "WARNING"
        for issue in issues
    )

    result = {
        "status": "FAILED" if errors else "PASSED",
        "total_issues": len(issues),
        "errors": errors,
        "warnings": warnings,
        "report": report
    }

    logger.info(
        "Validation completed | Status: %s | Errors: %s | Warnings: %s",
        result["status"],
        errors,
        warnings
    )

    return result


if __name__ == "__main__":

    from src.excel_reader import read_capex_workbook

    workbook_data = read_capex_workbook()

    result = validate_workbook(workbook_data)

    print("\n========== VALIDATION REPORT ==========\n")

    print("Status:", result["status"])
    print("Total issues:", result["total_issues"])
    print("Errors:", result["errors"])
    print("Warnings:", result["warnings"])

    if not result["report"].empty:
        print("\nIssue details:\n")
        print(result["report"].to_string(index=False))
    else:
        print("\nAll validation checks passed!")
