
"""
CAPEX Automation POC
Module: Merchant Matcher

Identifies merchants using Vendor Master and retrieves
their associated purchase-order records from SOP Dump.

Safety principle:
Never automatically select an ambiguous merchant.
"""

import logging
import re
import difflib

import pandas as pd

from src.excel_reader import read_capex_workbook


logger = logging.getLogger(__name__)


def normalize_text(value):
    """Normalize merchant names for reliable exact matching."""

    if pd.isna(value):
        return ""

    value = str(value).strip().casefold()

    # Normalize punctuation and repeated spaces.
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def find_merchant(data, search_term):
    """
    Resolve a merchant using its exact Vendor ID or name.

    Returns:
        Dictionary containing matching status and vendor details.
    """

    search_term = str(search_term).strip()

    if not search_term:
        return {
            "status": "INVALID_INPUT",
            "message": "Please enter a merchant name or Vendor ID."
        }

    vendors = data["Vendor_Master"].copy()

    required = ["Vendor_ID", "Merchant_Name"]

    if not all(col in vendors.columns for col in required):
        raise ValueError("Vendor Master has an invalid schema.")

    vendors["Normalized_ID"] = (
        vendors["Vendor_ID"].astype("string").str.strip().str.casefold()
    )

    vendors["Normalized_Name"] = (
        vendors["Merchant_Name"].apply(normalize_text)
    )

    # First check whether the input is a Vendor ID.
    id_matches = vendors[
        vendors["Normalized_ID"] == search_term.casefold()
    ]

    if len(id_matches) == 1:
        merchant = id_matches.iloc[0]

        return {
            "status": "FOUND",
            "vendor_id": str(merchant["Vendor_ID"]),
            "merchant_name": str(merchant["Merchant_Name"]),
            "match_type": "VENDOR_ID"
        }

    # Otherwise, perform normalized exact name matching.
    normalized_search = normalize_text(search_term)

    name_matches = vendors[
        vendors["Normalized_Name"] == normalized_search
    ]

    unique_ids = name_matches["Vendor_ID"].dropna().unique()

    if len(unique_ids) == 1:
        merchant = name_matches.iloc[0]

        return {
            "status": "FOUND",
            "vendor_id": str(merchant["Vendor_ID"]),
            "merchant_name": str(merchant["Merchant_Name"]),
            "match_type": "EXACT_NAME"
        }

    if len(unique_ids) > 1:
        return {
            "status": "AMBIGUOUS",
            "message": "Multiple vendor IDs match this merchant name.",
            "candidates": name_matches[
                ["Vendor_ID", "Merchant_Name"]
            ].drop_duplicates().to_dict("records")
        }

    # No exact match. Generate suggestions, but never auto-select.
    names = vendors["Normalized_Name"].dropna().unique()

    suggestions = difflib.get_close_matches(
        normalized_search,
        names,
        n=5,
        cutoff=0.55
    )

    candidate_rows = vendors[
        vendors["Normalized_Name"].isin(suggestions)
    ][["Vendor_ID", "Merchant_Name"]].drop_duplicates()

    return {
        "status": "NOT_FOUND",
        "message": "No exact merchant match found.",
        "suggestions": candidate_rows.to_dict("records")
    }


def get_merchant_records(data, merchant):
    """
    Retrieve SOP records using the resolved Vendor ID.

    Matching on Vendor ID prevents spelling variations
    in merchant names from accidentally excluding records.
    """

    if merchant["status"] != "FOUND":
        raise ValueError(
            "Cannot retrieve records without an unambiguous merchant."
        )

    sop = data["SOP_Dump"].copy()

    vendor_id = str(merchant["vendor_id"]).strip()

    matching_records = sop[
        sop["Vendor_ID"].astype("string").str.strip() == vendor_id
    ].copy()

    matching_records = matching_records.sort_values(
        by=["PO_Date", "PO_Number", "PO_Line_No"]
    )

    return matching_records.reset_index(drop=True)


def generate_merchant_summary(merchant, records):
    """Generate a summary of the merchant's purchase orders."""

    if records.empty:
        return {
            "merchant_name": merchant["merchant_name"],
            "vendor_id": merchant["vendor_id"],
            "total_po_lines": 0,
            "unique_purchase_orders": 0,
            "total_po_value": 0.0,
            "approval_status": {}
        }

    amounts = pd.to_numeric(
        records["PO_Line_Total_INR"],
        errors="coerce"
    )

    return {
        "merchant_name": merchant["merchant_name"],
        "vendor_id": merchant["vendor_id"],
        "total_po_lines": len(records),
        "unique_purchase_orders": records["PO_Number"].nunique(),
        "total_po_value": round(amounts.sum(), 2),
        "approval_status": (
            records["Approval_Status"]
            .value_counts()
            .to_dict()
        )
    }


def search_merchant(data, search_term):
    """Complete merchant search workflow."""

    merchant = find_merchant(data, search_term)

    if merchant["status"] != "FOUND":
        return {
            "merchant": merchant,
            "records": pd.DataFrame(),
            "summary": None
        }

    records = get_merchant_records(data, merchant)

    summary = generate_merchant_summary(
        merchant,
        records
    )

    logger.info(
        "Merchant search completed: %s | PO lines: %s",
        merchant["merchant_name"],
        len(records)
    )

    return {
        "merchant": merchant,
        "records": records,
        "summary": summary
    }


def print_search_result(result):

    merchant = result["merchant"]

    print("\n========== MERCHANT SEARCH ==========\n")

    print("Search status:", merchant["status"])

    if merchant["status"] != "FOUND":
        print(merchant.get("message", ""))

        if merchant.get("suggestions"):
            print("\nSuggested merchants:")
            for item in merchant["suggestions"]:
                print(item)

        if merchant.get("candidates"):
            print("\nAmbiguous matches:")
            for item in merchant["candidates"]:
                print(item)

        return

    summary = result["summary"]

    print("Merchant:", summary["merchant_name"])
    print("Vendor ID:", summary["vendor_id"])
    print("PO lines:", summary["total_po_lines"])
    print("Unique POs:", summary["unique_purchase_orders"])

    print(
        "Total PO value: ₹{:,.2f}".format(
            summary["total_po_value"]
        )
    )

    print("\nApproval status:")
    for status, count in summary["approval_status"].items():
        print(f"  {status}: {count}")

    print("\nMatching purchase orders:\n")

    display_columns = [
        "PO_Number",
        "PO_Line_No",
        "PO_Date",
        "Merchant_Name",
        "Project_Code",
        "Item_Description",
        "PO_Line_Total_INR",
        "Approval_Status"
    ]

    print(
        result["records"][display_columns].to_string(index=False)
    )


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    workbook_data = read_capex_workbook()

    # Initial demonstration merchant.
    result = search_merchant(
        workbook_data,
        "ABC Technologies"
    )

    print_search_result(result)
