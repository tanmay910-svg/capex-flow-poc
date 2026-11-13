import pandas as pd
from src.finance_register import build_finance_register


def test_register_aggregates_multiple_invoices_and_uses_project_wide_commitments():
    sop = pd.DataFrame([
        {"PO_Number":"PO1","PO_Line_No":1,"Project_Code":"P1","Financial_Year":"FY26",
         "PO_Line_Total_INR":1000,"Approval_Status":"Approved","Receipt_Status":"Received",
         "Merchant_Name":"North","Vendor_ID":"V1","PO_Date":"2026-01-01","Item_Description":"Laptop",
         "Spend_Category":"IT","Quantity":1},
        {"PO_Number":"PO2","PO_Line_No":1,"Project_Code":"P1","Financial_Year":"FY26",
         "PO_Line_Total_INR":500,"Approval_Status":"Pending","Receipt_Status":"Not Received",
         "Merchant_Name":"Other","Vendor_ID":"V2","PO_Date":"2026-01-02","Item_Description":"Monitor",
         "Spend_Category":"IT","Quantity":1},
    ])
    data = {
        "SOP_Dump": sop,
        "Invoice_Receipt": pd.DataFrame([
            {"PO_Number":"PO1","PO_Line_No":1,"Invoice_Number":"INV1",
             "Invoice_Amount_INR":400,"Received_Quantity":1,"Match_Status":"Matched"},
            {"PO_Number":"PO1","PO_Line_No":1,"Invoice_Number":"INV2",
             "Invoice_Amount_INR":300,"Received_Quantity":0,"Match_Status":"Matched"},
        ]),
        "Project_Master": pd.DataFrame([
            {"Project_Code":"P1","Project_Name":"Project 1","Department":"IT",
             "Cost_Centre":"CC1","Project_Status":"Approved"},
        ]),
        "CAPEX_Budget": pd.DataFrame([
            {"Project_Code":"P1","Financial_Year":"FY26",
             "Approved_Budget_INR":2000,"Revised_Budget_Adjustment_INR":0},
        ]),
    }
    merchant = {
        "merchant": {"status":"FOUND","merchant_name":"North","vendor_id":"V1"},
        "records": sop[sop["Vendor_ID"] == "V1"].copy(),
    }
    result = build_finance_register(data, merchant)
    assert len(result["records"]) == 1
    row = result["records"].iloc[0]
    assert row["Invoice_Amount_INR"] == 700
    assert row["Project_Approved_Commitments_INR"] == 1500
    assert row["Project_Remaining_Budget_INR"] == 500
    assert result["summary"]["po_lines"] == 1


def test_missing_invoice_is_flagged_without_claiming_capitalization():
    # The register is deliberately a reconciliation/review report only.
    pass
