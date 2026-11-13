# CAPEX Automation POC

Synthetic-data proof-of-concept for extracting merchant-related purchase order records from an SOP workbook, reconciling invoice and receipt information, and producing a finance-oriented review report.

## Current branches
- `main`: Phase 1 merchant PO extraction and basic report.
- `phase-2-finance-register`: Phase 2 finance register calculation and report design, developed separately so the deployed main branch is not changed.

## Phase 2 proposal
The proposed output workbook has four tabs:
1. CAPEX Register — selected merchant PO lines with vendor/project/budget/invoice and review fields.
2. Project Summary — project/financial-year budget and project-wide approved commitments.
3. Reconciliation — PO/invoice and budget/commitment review checks.
4. Read Me & Assumptions — definitions and limitations.

This is a generic synthetic POC layout, not the employer's template. No company data is included or requested.

## Accounting boundaries
PO value, invoice value, receipt quantity, paid expenditure, approved commitment and capitalized asset cost are distinct. The POC does not determine paid amounts, capitalization eligibility, asset class, useful life, depreciation, tax treatment or journal entries. Finance policy and review are required before production use.

## Safety
Do not upload company data or connect company systems until the employer's IT and data owners explicitly approve the environment, data flow, security controls and deployment model.


## Phase 2 — Finance Register & Reconciliation

The `phase-2-finance-register` branch adds a finance review workflow to the Streamlit dashboard. After the existing merchant CAPEX processing, select **Build Finance Register** to view:
- CAPEX Register with PO, invoice, receipt and budget context.
- Project Summary with project-wide approved commitments and remaining budget.
- Reconciliation with PO/invoice variance and budget checks.

Use **Generate Finance Excel Workbook** to download a four-tab workbook. The generic template is created automatically on first use under `data/templates/`.

All figures and records in the public demo are synthetic. Approved commitment is an illustrative assumption, not a confirmed company accounting rule. The app does not decide capitalization eligibility, payment, depreciation or journal entries. Do not upload company information without explicit IT and data-owner approval.
