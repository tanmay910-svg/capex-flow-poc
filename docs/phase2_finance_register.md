# CAPEX FLOW — Phase 2 Finance Register

## Purpose
The Phase 1 output is a merchant-focused PO-line report. Phase 2 proposes a finance-oriented report adding project/FY budget context, project-wide commitments, invoice reconciliation and exception flags.

## Output workbook
- CAPEX Register: one row per selected merchant PO line.
- Project Summary: one row per project and financial year; commitments are calculated using all vendors in the complete uploaded SOP Dump.
- Reconciliation: PO-to-invoice and budget-to-commitment review checks.
- Read Me & Assumptions: definitions, calculation assumptions and limitations.

## Measure definitions
- PO value: PO line amount from SOP_Dump.
- Invoice value: sum of invoice records linked to the PO line; not necessarily paid expenditure.
- Uninvoiced PO value: max(PO value - invoice value, 0), an exposure indicator only.
- Invoice variance: invoice value minus PO value.
- Approved commitment: the synthetic POC assumes Approval_Status == Approved. Finance must confirm the applicable rule.
- Project commitments: approved PO value across all vendors in the uploaded SOP Dump for the same project and financial year.
- Remaining budget: revised budget minus project-wide approved commitments.
- Receipt status and received quantity do not establish payment or capitalization.
- No capitalization, depreciation, useful-life, tax or journal-entry determination is made.

## Review flags
Approval, receipt, missing invoice/budget, invoice variance, project status and project budget overruns are surfaced for human review. A clear flag means only that configured demo checks passed.

## Template status
This is a proposed generic POC report, not an employer-approved CAPEX template. Replace field mappings and rules only after the actual template and Finance policy are made available through approved channels.
