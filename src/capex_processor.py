
"""
CAPEX Automation POC
Module: CAPEX Processing Engine

Combines merchant PO lines with invoice, project and
budget information to produce a consolidated dataset.

Important:
This module performs data enrichment and financial analysis.
It does not independently determine accounting capitalization eligibility.
"""

import logging
import pandas as pd


logger = logging.getLogger(__name__)


def normalize_key(series):
    """Normalize identifiers before joining datasets."""

    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def require_columns(df, columns, dataset_name):
    """Ensure a dataset contains all required fields."""

    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"{dataset_name} is missing columns: {missing}"
        )


def prepare_invoice_data(invoices):
    """
    Aggregate invoices at PO-line level.

    Multiple invoices against one PO line must not
    multiply the original PO value during merging.
    """

    invoices = invoices.copy()

    require_columns(
        invoices,
        [
            "PO_Number",
            "PO_Line_No",
            "Invoice_Number",
            "Invoice_Amount_INR",
            "Received_Quantity",
            "Match_Status"
        ],
        "Invoice_Receipt"
    )

    invoices["_PO_Key"] = normalize_key(invoices["PO_Number"])
    invoices["_Line_Key"] = normalize_key(invoices["PO_Line_No"])

    invoices["Invoice_Amount_INR"] = pd.to_numeric(
        invoices["Invoice_Amount_INR"],
        errors="coerce"
    )

    invoices["Received_Quantity"] = pd.to_numeric(
        invoices["Received_Quantity"],
        errors="coerce"
    )

    grouped = (
        invoices.groupby(
            ["_PO_Key", "_Line_Key"],
            dropna=False
        )
        .agg(
            Invoice_Count=("Invoice_Number", "nunique"),
            Invoice_Amount_INR=("Invoice_Amount_INR", "sum"),
            Received_Quantity=("Received_Quantity", "sum"),
            Invoice_Match_Status=(
                "Match_Status",
                lambda x: " | ".join(
                    sorted(x.dropna().astype(str).unique())
                )
            )
        )
        .reset_index()
    )

    return grouped


def prepare_project_data(projects):
    """Select and prepare project reference information."""

    require_columns(
        projects,
        [
            "Project_Code",
            "Project_Name",
            "Department",
            "Cost_Centre",
            "Project_Status"
        ],
        "Project_Master"
    )

    projects = projects.copy()

    projects["_Project_Key"] = normalize_key(
        projects["Project_Code"]
    )

    return projects[
        [
            "_Project_Key",
            "Cost_Centre",
            "Project_Status"
        ]
    ].drop_duplicates("_Project_Key")


def prepare_budget_data(budgets):
    """Prepare approved and adjusted project budgets."""

    require_columns(
        budgets,
        [
            "Project_Code",
            "Financial_Year",
            "Approved_Budget_INR",
            "Revised_Budget_Adjustment_INR"
        ],
        "CAPEX_Budget"
    )

    budgets = budgets.copy()

    budgets["_Project_Key"] = normalize_key(
        budgets["Project_Code"]
    )

    budgets["_FY_Key"] = normalize_key(
        budgets["Financial_Year"]
    )

    budgets["Approved_Budget_INR"] = pd.to_numeric(
        budgets["Approved_Budget_INR"],
        errors="coerce"
    )

    budgets["Revised_Budget_Adjustment_INR"] = pd.to_numeric(
        budgets["Revised_Budget_Adjustment_INR"],
        errors="coerce"
    )

    budgets["Revised_Budget_INR"] = (
        budgets["Approved_Budget_INR"]
        + budgets["Revised_Budget_Adjustment_INR"]
    )

    return budgets[
        [
            "_Project_Key",
            "_FY_Key",
            "Approved_Budget_INR",
            "Revised_Budget_Adjustment_INR",
            "Revised_Budget_INR"
        ]
    ]


def calculate_project_commitments(sop):
    """
    Calculate project-wide approved PO commitments.

    This intentionally uses the complete SOP dataset,
    not just the selected merchant's records.

    Prototype assumption:
    Only Approval_Status == 'Approved' counts as an
    approved commitment. This must be confirmed by Finance.
    """

    sop = sop.copy()

    sop["_Project_Key"] = normalize_key(
        sop["Project_Code"]
    )

    sop["_FY_Key"] = normalize_key(
        sop["Financial_Year"]
    )

    sop["PO_Line_Total_INR"] = pd.to_numeric(
        sop["PO_Line_Total_INR"],
        errors="coerce"
    )

    approved = sop[
        sop["Approval_Status"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .eq("approved")
    ].copy()

    commitments = (
        approved.groupby(
            ["_Project_Key", "_FY_Key"]
        )["PO_Line_Total_INR"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "PO_Line_Total_INR":
                "Project_Approved_Commitments_INR"
            }
        )
    )

    return commitments


def calculate_merchant_commitments(merchant_records):
    """Calculate approved commitments for the selected merchant."""

    records = merchant_records.copy()

    records["_Project_Key"] = normalize_key(
        records["Project_Code"]
    )

    records["_FY_Key"] = normalize_key(
        records["Financial_Year"]
    )

    records["PO_Line_Total_INR"] = pd.to_numeric(
        records["PO_Line_Total_INR"],
        errors="coerce"
    )

    approved = records[
        records["Approval_Status"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .eq("approved")
    ]

    return (
        approved.groupby(
            ["_Project_Key", "_FY_Key"]
        )["PO_Line_Total_INR"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "PO_Line_Total_INR":
                "Merchant_Approved_Commitment_INR"
            }
        )
    )


def add_review_flags(df):
    """Add transparent workflow flags for human review."""

    df = df.copy()

    flags = []

    for _, row in df.iterrows():

        current_flags = []

        if row["Approval_Status"] != "Approved":
            current_flags.append("CHECK_APPROVAL")

        if row["Receipt_Status"] != "Received":
            current_flags.append("CHECK_RECEIPT")

        if row["Invoice_Count"] == 0:
            current_flags.append("NO_INVOICE_FOUND")

        if row["Invoice_Amount_INR"] > row["PO_Line_Total_INR"]:
            current_flags.append("INVOICE_EXCEEDS_PO_VALUE")

        if row["Invoice_Amount_INR"] < row["PO_Line_Total_INR"]:
            current_flags.append("INVOICE_BELOW_PO_VALUE")

        if pd.isna(row["Revised_Budget_INR"]):
            current_flags.append("BUDGET_NOT_FOUND")

        elif (
            row["Project_Remaining_Budget_INR"] < 0
        ):
            current_flags.append("PROJECT_BUDGET_EXCEEDED")

        if not current_flags:
            current_flags.append("READY_FOR_FINANCE_REVIEW")

        flags.append(" | ".join(current_flags))

    df["Review_Flag"] = flags

    return df


def process_merchant_capex(data, merchant_result):
    """
    Main CAPEX processing function.

    Arguments:
        data: Dictionary containing workbook DataFrames.
        merchant_result: Result returned by search_merchant().

    Returns:
        Dictionary containing processed records and summaries.
    """

    logger.info("Starting CAPEX processing...")

    if merchant_result["merchant"]["status"] != "FOUND":
        raise ValueError("Merchant must be resolved before processing.")

    merchant_records = merchant_result["records"].copy()

    if merchant_records.empty:
        raise ValueError("No purchase-order records found.")

    sop = data["SOP_Dump"].copy()
    invoices = data["Invoice_Receipt"].copy()
    projects = data["Project_Master"].copy()
    budgets = data["CAPEX_Budget"].copy()

    require_columns(
        merchant_records,
        [
            "PO_Number",
            "PO_Line_No",
            "Project_Code",
            "Financial_Year",
            "PO_Line_Total_INR",
            "Approval_Status",
            "Receipt_Status"
        ],
        "Merchant Records"
    )

    # Prepare join keys.
    merchant_records["_PO_Key"] = normalize_key(
        merchant_records["PO_Number"]
    )

    merchant_records["_Line_Key"] = normalize_key(
        merchant_records["PO_Line_No"]
    )

    merchant_records["_Project_Key"] = normalize_key(
        merchant_records["Project_Code"]
    )

    merchant_records["_FY_Key"] = normalize_key(
        merchant_records["Financial_Year"]
    )

    merchant_records["PO_Line_Total_INR"] = pd.to_numeric(
        merchant_records["PO_Line_Total_INR"],
        errors="coerce"
    )

    # 1. Enrich with aggregated invoice information.
    invoice_data = prepare_invoice_data(invoices)

    processed = merchant_records.merge(
        invoice_data,
        on=["_PO_Key", "_Line_Key"],
        how="left",
        validate="one_to_one"
    )

    processed["Invoice_Count"] = (
        processed["Invoice_Count"].fillna(0).astype(int)
    )

    processed["Invoice_Amount_INR"] = (
        processed["Invoice_Amount_INR"].fillna(0)
    )

    processed["Received_Quantity"] = (
        processed["Received_Quantity"].fillna(0)
    )

    processed["Invoice_Match_Status"] = (
        processed["Invoice_Match_Status"].fillna("NO_INVOICE")
    )

    # 2. Enrich with project information.
    project_data = prepare_project_data(projects)

    processed = processed.merge(
        project_data,
        on="_Project_Key",
        how="left",
        validate="many_to_one"
    )

    # 3. Enrich with financial-year budget.
    budget_data = prepare_budget_data(budgets)

    processed = processed.merge(
        budget_data,
        on=["_Project_Key", "_FY_Key"],
        how="left",
        validate="many_to_one"
    )

    # 4. Calculate project-wide commitments.
    project_commitments = calculate_project_commitments(sop)

    processed = processed.merge(
        project_commitments,
        on=["_Project_Key", "_FY_Key"],
        how="left",
        validate="many_to_one"
    )

    processed["Project_Approved_Commitments_INR"] = (
        processed["Project_Approved_Commitments_INR"].fillna(0)
    )

    # 5. Calculate selected merchant's approved commitments.
    merchant_commitments = calculate_merchant_commitments(
        merchant_records
    )

    processed = processed.merge(
        merchant_commitments,
        on=["_Project_Key", "_FY_Key"],
        how="left",
        validate="many_to_one"
    )

    processed["Merchant_Approved_Commitment_INR"] = (
        processed["Merchant_Approved_Commitment_INR"].fillna(0)
    )

    # 6. Calculate financial analysis fields.
    processed["Invoice_Variance_INR"] = (
        processed["Invoice_Amount_INR"]
        - processed["PO_Line_Total_INR"]
    )

    processed["Uninvoiced_PO_Value_INR"] = (
        processed["PO_Line_Total_INR"]
        - processed["Invoice_Amount_INR"]
    ).clip(lower=0)

    processed["Project_Remaining_Budget_INR"] = (
        processed["Revised_Budget_INR"]
        - processed["Project_Approved_Commitments_INR"]
    )

    # 7. Add review flags.
    processed = add_review_flags(processed)

    # Remove internal join keys.
    internal_columns = [
        "_PO_Key",
        "_Line_Key",
        "_Project_Key",
        "_FY_Key"
    ]

    processed.drop(
        columns=internal_columns,
        inplace=True,
        errors="ignore"
    )

    # Summary.
    summary = {
        "merchant_name": merchant_result["merchant"]["merchant_name"],
        "vendor_id": merchant_result["merchant"]["vendor_id"],
        "total_po_lines": len(processed),
        "unique_purchase_orders": processed["PO_Number"].nunique(),
        "total_po_value_inr": round(
            processed["PO_Line_Total_INR"].sum(), 2
        ),
        "total_invoice_value_inr": round(
            processed["Invoice_Amount_INR"].sum(), 2
        ),
        "approved_commitment_inr": round(
            processed["Merchant_Approved_Commitment_INR"]
            .drop_duplicates()
            .sum(), 2
        ),
        "projects_involved": processed["Project_Code"].nunique(),
        "records_requiring_review": int(
            processed["Review_Flag"].ne("READY_FOR_FINANCE_REVIEW").sum()
        )
    }

    logger.info(
        "CAPEX processing completed | Merchant: %s | Records: %s",
        summary["merchant_name"],
        summary["total_po_lines"]
    )

    return {
        "records": processed,
        "summary": summary
    }


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    from src.excel_reader import read_capex_workbook
    from src.merchant_matcher import search_merchant

    workbook_data = read_capex_workbook()

    merchant_result = search_merchant(
        workbook_data,
        "ABC Technologies"
    )

    result = process_merchant_capex(
        workbook_data,
        merchant_result
    )

    print("\n========== CAPEX PROCESSING SUMMARY ==========\n")

    for key, value in result["summary"].items():
        print(f"{key}: {value}")

    print("\n========== PROCESSED RECORDS ==========\n")

    display_columns = [
        "PO_Number",
        "Project_Code",
        "PO_Line_Total_INR",
        "Invoice_Amount_INR",
        "Uninvoiced_PO_Value_INR",
        "Project_Remaining_Budget_INR",
        "Review_Flag"
    ]

    print(
        result["records"][display_columns].to_string(index=False)
    )
