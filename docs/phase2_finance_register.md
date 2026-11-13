# CAPEX FLOW — Phase 2 Finance Register

## Status
Synthetic proof-of-concept design. This is not an employer-approved CAPEX template or accounting policy implementation.

## Output workbook
- **CAPEX Register:** one row per selected merchant PO line.
- **Project Summary:** one row per project/financial year represented by the merchant; project commitments include all vendors in the uploaded SOP Dump.
- **Reconciliation:** PO-to-invoice and revised-budget-to-commitment checks.
- **Read Me & Assumptions:** definitions, formulas and accounting boundaries.

## Measure definitions
- PO value: purchase-order line amount from SOP Dump.
- Invoice value: sum of invoice amounts matched to a PO line; not necessarily paid expenditure.
- Uninvoiced PO value: max(PO value - invoice value, 0), an exposure indicator only.
- Invoice variance: invoice value - PO value.
- Approved commitment: this POC assumes Approval_Status == Approved. Finance must confirm a production rule.
- Project commitments: approved PO value across all vendors in the full uploaded SOP Dump for the same project and financial year.
- Remaining budget: revised budget - project-wide approved commitments.
- Receipt quantities do not establish invoice payment or capitalization.
- No capitalization, depreciation, useful-life, tax or journal-entry determination is made.

## Human review flags
Approval, receipt, missing invoice/budget, invoice variance, project status and project budget overruns are surfaced for human review. A clean row means only that configured demo checks passed; it is not an approval or capitalization decision.

## Source data
The existing input workbook remains separate and includes SOP_Dump, Vendor_Master, Project_Master, CAPEX_Budget and Invoice_Receipt.
