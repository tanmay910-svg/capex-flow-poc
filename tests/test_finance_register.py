import pandas as pd
from src.finance_register import build_finance_register


def sample_data():
    sop = pd.DataFrame([
        {"PO_Number":"PO1","PO_Line_No":1,"Project_Code":"P1","Financial_Year":"FY26",
         "PO_Line_Total_INR":1000,"Approval_Status":"Approved","Receipt_Status":"Received",
         "Merchant_Name":"North","Vendor_ID":"V1","Project_Name":"Project 1","Department":"IT","PO_Date":"2026-01-01","Item_Description":"Laptop",
         "Spend_Category":"IT","Quantity":1},
        {"PO_Number":"PO2","PO_Line_No":1,"Project_Code":"P1","Financial_Year":"FY26",
         "PO_Line_Total_INR":500,"Approval_Status":"Pending","Receipt_Status":"Not Received",
         "Merchant_Name":"Other","Vendor_ID":"V2","Project_Name":"Project 1","Department":"IT","PO_Date":"2026-01-02","Item_Description":"Monitor",
         "Spend_Category":"IT","Quantity":1},
    ])
    return {
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


def merchant_result(data):
    sop = data["SOP_Dump"]
    return {
        "merchant": {"status":"FOUND","merchant_name":"North","vendor_id":"V1"},
        "records": sop[sop["Vendor_ID"] == "V1"].copy(),
    }


def test_register_aggregates_multiple_invoices_and_project_wide_commitments():
    data = sample_data()
    result = build_finance_register(data, merchant_result(data))
    assert len(result["records"]) == 1
    row = result["records"].iloc[0]
    assert row["Invoice_Amount_INR"] == 700
    assert row["Project_Approved_Commitments_INR"] == 1000
    assert row["Project_Remaining_Budget_INR"] == 1000
    assert result["summary"]["po_lines"] == 1


def test_review_flags_show_missing_invoice_and_never_claim_capitalization():
    data = sample_data()
    data["Invoice_Receipt"] = data["Invoice_Receipt"].iloc[0:0]
    result = build_finance_register(data, merchant_result(data))
    assert "NO_INVOICE_FOUND" in result["records"].iloc[0]["Review_Flag"]
    assert "Capitalization_Status" not in result["records"].columns
