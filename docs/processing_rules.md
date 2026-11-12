# Processing rules — POC baseline

## Input checks
- Workbook and required worksheets exist.
- Header row and required columns exist.
- Required identifiers are not blank.
- Dates parse successfully.
- Numeric fields parse and are non-negative.
- PO line key (`PO_Number`, `PO_Line_No`) is unique.
- Vendor, project and project-financial-year budget references resolve.
- Invoice references resolve to an existing PO line.
- PO line total reconciles to the synthetic calculation within ₹0.01.

## Merchant selection
- Exact normalized merchant-name match is allowed as a search convenience.
- Resolve the selected merchant to `Vendor_ID`.
- Show merchant ID and match count before generating output.
- Ambiguous/fuzzy matching requires explicit user confirmation.

## Report generation
- Filter by selected `Vendor_ID` and selected financial year.
- Enrich with vendor, project and budget reference data.
- Aggregate invoice/receipt information by PO line before joining.
- Preserve one output row per PO line.
- Keep source PO value and invoice value in separate columns.
- Add exception flags for pending/rejected approvals, missing invoice, unmatched invoice, partial/no receipt, inactive vendor, missing project/budget and other data-quality issues.
- Do not label a line as capitalizable solely because its PO is approved.
- Populate a copy of the workbook template; never overwrite source input files.

## Human review
The POC can flag items for review. It cannot set capitalization eligibility, useful life, depreciation method, tax treatment or journal entries unless the employer supplies approved policy and authorization for those rules.
