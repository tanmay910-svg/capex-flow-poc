
from src.excel_reader import read_capex_workbook
from src.validator import validate_workbook


def test_incorrect_vendor_id():

    print("\n========== VENDOR VALIDATION TEST ==========\n")

    # Step 1: Load the original synthetic workbook.
    data = read_capex_workbook()

    # Step 2: Create an independent copy of its data.
    test_data = {
        sheet: df.copy(deep=True)
        for sheet, df in data.items()
    }

    # Step 3: Select the first invoice.
    invoices = test_data["Invoice_Receipt"]
    first_index = invoices.index[0]

    original_vendor = invoices.loc[first_index, "Vendor_ID"]

    # Step 4: Introduce an incorrect vendor ID.
    invoices.loc[first_index, "Vendor_ID"] = "VEN-INVALID-999"

    print("Original Vendor ID:", original_vendor)
    print("Modified Vendor ID:", invoices.loc[first_index, "Vendor_ID"])

    # Step 5: Run the existing validation engine.
    result = validate_workbook(test_data)

    print("\n========== VALIDATION RESULT ==========\n")
    print("Status:", result["status"])
    print("Errors:", result["errors"])
    print("Warnings:", result["warnings"])

    if not result["report"].empty:
        print("\nDetected issues:\n")
        print(result["report"].to_string(index=False))

    # Step 6: Verify that the correct error was detected.
    messages = (
        result["report"]["Message"].astype(str).tolist()
        if "Message" in result["report"].columns
        else result["report"].astype(str).agg(" ".join, axis=1).tolist()
    )

    assert any(
        "Invoice Vendor_ID does not match" in message
        for message in messages
    ), "FAILED: Incorrect invoice vendor was not detected!"

    assert result["status"] != "PASSED", (
        "FAILED: Validation incorrectly passed invalid vendor data!"
    )

    print("\nTEST PASSED: Incorrect vendor detected successfully!")


if __name__ == "__main__":
    test_incorrect_vendor_id()
