# Phase 2 implementation notes

- Work is isolated on `phase-2-finance-register`; `main` remains unchanged.
- `src/finance_register.py` builds finance-oriented register, project summary and reconciliation dataframes.
- `tests/test_finance_register.py` covers multi-invoice aggregation, project-wide commitment calculation, and review-only behavior.
- `CAPEX_FLOW_Proposed_Finance_Register_Template.xlsx` is a separate four-tab blank template.
- Next: finish workbook generator, integrate the Streamlit branch, run the test suite against the synthetic workbook, then review the downloadable Excel output before deployment.
