"""
Finance-oriented CAPEX register calculations for the synthetic POC.
This is a review-support layer, not an accounting-policy or capitalization engine.
"""
import pandas as pd
from src.capex_processor import (
    normalize_key, prepare_invoice_data, prepare_project_data,
    prepare_budget_data, calculate_project_commitments,
    calculate_merchant_commitments, require_columns,
)


def build_finance_register(data, merchant_result):
    """Build register, project summary and reconciliation datasets."""
    if merchant_result["merchant"]["status"] != "FOUND":
        raise ValueError("Merchant must be resolved before building the register.")
    selected = merchant_result["records"].copy()
    if selected.empty:
        raise ValueError("No PO lines found for the selected merchant.")
    sop = data["SOP_Dump"].copy()

    require_columns(selected, [
        "PO_Number", "PO_Line_No", "Project_Code", "Financial_Year",
        "PO_Line_Total_INR", "Approval_Status", "Receipt_Status"
    ], "Selected SOP records")

    selected["_PO_Key"] = normalize_key(selected["PO_Number"])
    selected["_Line_Key"] = normalize_key(selected["PO_Line_No"])
    selected["_Project_Key"] = normalize_key(selected["Project_Code"])
    selected["_FY_Key"] = normalize_key(selected["Financial_Year"])
    selected["PO_Line_Total_INR"] = pd.to_numeric(
        selected["PO_Line_Total_INR"], errors="coerce"
    )

    register = selected.merge(
        prepare_invoice_data(data["Invoice_Receipt"]),
        on=["_PO_Key", "_Line_Key"], how="left", validate="one_to_one"
    )
    register["Invoice_Count"] = register["Invoice_Count"].fillna(0).astype(int)
    register["Invoice_Amount_INR"] = register["Invoice_Amount_INR"].fillna(0)
    register["Received_Quantity"] = register["Received_Quantity"].fillna(0)
    register["Invoice_Match_Status"] = register["Invoice_Match_Status"].fillna("NO_INVOICE")

    register = register.merge(
        prepare_project_data(data["Project_Master"]),
        on="_Project_Key", how="left", validate="many_to_one"
    )
    register = register.merge(
        prepare_budget_data(data["CAPEX_Budget"]),
        on=["_Project_Key", "_FY_Key"], how="left", validate="many_to_one"
    )

    register = register.merge(
        calculate_project_commitments(sop),
        on=["_Project_Key", "_FY_Key"], how="left", validate="many_to_one"
    )
    register["Project_Approved_Commitments_INR"] = (
        register["Project_Approved_Commitments_INR"].fillna(0)
    )
    register = register.merge(
        calculate_merchant_commitments(selected),
        on=["_Project_Key", "_FY_Key"], how="left", validate="many_to_one"
    )
    register["Merchant_Approved_Commitment_INR"] = (
        register["Merchant_Approved_Commitment_INR"].fillna(0)
    )

    register["Invoice_Variance_INR"] = (
        register["Invoice_Amount_INR"] - register["PO_Line_Total_INR"]
    )
    register["Uninvoiced_PO_Value_INR"] = (
        register["PO_Line_Total_INR"] - register["Invoice_Amount_INR"]
    ).clip(lower=0)
    register["Project_Remaining_Budget_INR"] = (
        register["Revised_Budget_INR"] - register["Project_Approved_Commitments_INR"]
    )
    register["Budget_Utilization_Pct"] = (
        register["Project_Approved_Commitments_INR"]
        .div(register["Revised_Budget_INR"].where(register["Revised_Budget_INR"] != 0))
        .mul(100)
    )

    def review_flags(row):
        flags = []
        if str(row.get("Approval_Status", "")).strip().casefold() != "approved":
            flags.append("CHECK_APPROVAL")
        if str(row.get("Receipt_Status", "")).strip().casefold() != "received":
            flags.append("CHECK_RECEIPT")
        if row["Invoice_Count"] == 0:
            flags.append("NO_INVOICE_FOUND")
        if row["Invoice_Amount_INR"] > row["PO_Line_Total_INR"] + 0.01:
            flags.append("INVOICE_EXCEEDS_PO_VALUE")
        elif row["Invoice_Amount_INR"] < row["PO_Line_Total_INR"] - 0.01:
            flags.append("INVOICE_BELOW_PO_VALUE")
        if pd.isna(row.get("Revised_Budget_INR")):
            flags.append("BUDGET_NOT_FOUND")
        elif row["Project_Remaining_Budget_INR"] < 0:
            flags.append("PROJECT_BUDGET_EXCEEDED")
        if str(row.get("Project_Status", "")).strip().casefold() not in ("approved", "active"):
            flags.append("CHECK_PROJECT_STATUS")
        return " | ".join(flags) if flags else "DEMO_CHECKS_PASSED"

    register["Review_Flag"] = register.apply(review_flags, axis=1)

    group_cols = ["Project_Code", "Project_Name", "Financial_Year"]
    project_summary = (
        register.groupby(group_cols, dropna=False)
        .agg(
            Approved_Budget_INR=("Approved_Budget_INR", "first"),
            Budget_Adjustment_INR=("Revised_Budget_Adjustment_INR", "first"),
            Revised_Budget_INR=("Revised_Budget_INR", "first"),
            Project_Approved_Commitments_INR=("Project_Approved_Commitments_INR", "first"),
            Selected_Merchant_Commitment_INR=("Merchant_Approved_Commitment_INR", "first"),
            Selected_Merchant_PO_Value_INR=("PO_Line_Total_INR", "sum"),
            Selected_Merchant_Invoice_Value_INR=("Invoice_Amount_INR", "sum"),
        ).reset_index()
    )
    project_summary["Project_Remaining_Budget_INR"] = (
        project_summary["Revised_Budget_INR"] - project_summary["Project_Approved_Commitments_INR"]
    )
    project_summary["Budget_Utilization_Pct"] = (
        project_summary["Project_Approved_Commitments_INR"]
        .div(project_summary["Revised_Budget_INR"].where(project_summary["Revised_Budget_INR"] != 0))
        .mul(100)
    )

    reconciliation = register[[
        "PO_Number", "PO_Line_No", "Project_Code", "Financial_Year",
        "PO_Line_Total_INR", "Invoice_Amount_INR", "Invoice_Variance_INR",
        "Approved_Budget_INR", "Revised_Budget_INR",
        "Project_Approved_Commitments_INR", "Project_Remaining_Budget_INR",
        "Review_Flag"
    ]].copy()
    reconciliation["PO_Invoice_Check"] = reconciliation["Invoice_Variance_INR"].apply(
        lambda value: "REVIEW" if abs(value) > 0.01 else "MATCH"
    )
    reconciliation["Budget_Check"] = reconciliation["Project_Remaining_Budget_INR"].apply(
        lambda value: "OVER_BUDGET" if pd.notna(value) and value < 0
        else ("NO_BUDGET" if pd.isna(value) else "WITHIN_BUDGET")
    )

    register.drop(
        columns=["_PO_Key", "_Line_Key", "_Project_Key", "_FY_Key"],
        inplace=True, errors="ignore"
    )
    priority = [
        "Merchant_Name", "Vendor_ID", "Project_Code", "Project_Name",
        "Department", "Cost_Centre", "Financial_Year", "PO_Number",
        "PO_Line_No", "PO_Date", "Item_Description", "Spend_Category",
        "Quantity", "PO_Line_Total_INR", "Approval_Status", "Receipt_Status",
        "Invoice_Count", "Invoice_Amount_INR", "Received_Quantity",
        "Invoice_Match_Status", "Approved_Budget_INR",
        "Revised_Budget_Adjustment_INR", "Revised_Budget_INR",
        "Project_Approved_Commitments_INR", "Merchant_Approved_Commitment_INR",
        "Project_Remaining_Budget_INR", "Budget_Utilization_Pct",
        "Invoice_Variance_INR", "Uninvoiced_PO_Value_INR", "Review_Flag",
    ]
    register = register[[c for c in priority if c in register.columns] +
                        [c for c in register.columns if c not in priority]]

    summary = {
        "merchant_name": merchant_result["merchant"]["merchant_name"],
        "vendor_id": merchant_result["merchant"]["vendor_id"],
        "po_lines": int(len(register)),
        "po_value_inr": round(float(register["PO_Line_Total_INR"].sum()), 2),
        "invoice_value_inr": round(float(register["Invoice_Amount_INR"].sum()), 2),
        "merchant_approved_commitment_inr": round(
            float(register["Merchant_Approved_Commitment_INR"].drop_duplicates().sum()), 2
        ),
        "project_count": int(register["Project_Code"].nunique()),
        "review_lines": int(register["Review_Flag"].ne("DEMO_CHECKS_PASSED").sum()),
        "project_budget_overruns": int(project_summary["Project_Remaining_Budget_INR"].lt(0).sum()),
    }
    return {
        "records": register,
        "project_summary": project_summary,
        "reconciliation": reconciliation,
        "summary": summary,
    }
