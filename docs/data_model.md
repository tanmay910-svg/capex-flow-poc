# Data model and relationship design

## Grain of each dataset

| Dataset | One row represents | Primary key |
|---|---|---|
| SOP_Dump | One purchase-order line | `PO_Number + PO_Line_No` |
| Vendor_Master | One merchant/vendor | `Vendor_ID` |
| Project_Master | One project | `Project_Code` |
| CAPEX_Budget | One project budget per financial year | `Project_Code + Financial_Year` |
| Invoice_Receipt | One invoice/receipt matching record | `Invoice_Number` |
| CAPEX output | One selected PO line, enriched with related details | `PO_Number + PO_Line_No` |

## Relationships

- Vendor master (1) → (many) SOP dump lines, joined by `Vendor_ID`.
- Project master (1) → (many) SOP dump lines, joined by `Project_Code`.
- Budget (1) → (many) SOP dump lines for a project and financial year, joined by `Project_Code + Financial_Year`.
- SOP dump line (1) → (many) invoice/receipt records, joined by `PO_Number + PO_Line_No`.

The synthetic file currently has at most one invoice row for each PO line. The implementation should nevertheless support multiple invoices per PO line.

## Merchant search and matching

1. Prefer the stable `Vendor_ID` once a merchant has been selected.
2. Normalize the entered merchant name (trim, collapse repeated whitespace, case-insensitive comparison).
3. If exactly one vendor matches, show the selected vendor and its ID before generation.
4. If multiple candidates or only a fuzzy match exist, require user confirmation. Never silently choose a fuzzy match.
5. Filter SOP rows by `Vendor_ID`, not by unverified free-text merchant names.

## Amount semantics

- `PO_Line_Total_INR`: order value from the PO line; synthetic formula is quantity × unit price − discount + tax.
- `Invoice_Amount_INR`: amount represented by invoice records; may be partial and may differ from PO value.
- `Received_Quantity`: quantity recorded as received; does not establish invoice payment.
- Committed spend, actual spend, paid amount and capitalized cost must be separately defined by Finance policy. Do not infer one from another.
- A budget comparison should use a clearly named measure and should not imply that PO value is capitalized expenditure.

## Output grain and duplicate prevention

The output remains one row per PO line. If several invoice records match a PO line, aggregate invoice amounts and received quantities in a separate grouped summary before joining to SOP data. Do not join raw one-to-many invoice rows directly to PO lines and accidentally duplicate PO values.
