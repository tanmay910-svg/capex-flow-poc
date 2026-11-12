# Phase 1 — synthetic workbook inspection

Workbook inspected: `CAPEX_POC_Synthetic_Data_Pack.xlsx`.

- SOP_Dump: 145 PO line rows; 145 unique PO numbers; 145 unique PO-line keys.
- Vendor_Master: 10 vendors.
- Project_Master: 15 projects.
- CAPEX_Budget: 15 project-year budget rows.
- Invoice_Receipt: 110 invoice/receipt records.
- SOP rows have no unknown vendor IDs or project codes against the reference sheets.
- All SOP project/financial-year pairs have a matching budget row.
- All invoice/receipt rows reference an existing PO line.
- No duplicate invoice-to-PO-line keys in this particular synthetic sample; implementation should still support multiple invoices per line.
- No negative quantities or amounts detected.
- All synthetic PO line totals reconcile to quantity × unit price − discount + tax.
- ABC Technologies sample: 9 PO lines, 9 PO numbers, PO line total ₹84,23,300; 6 invoice/receipt records.

These results describe only the generated synthetic sample. They do not validate any employer data or accounting policy.
