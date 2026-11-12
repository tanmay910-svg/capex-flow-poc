# CAPEX Automation POC

A local proof-of-concept that generates a proposed CAPEX workbook from synthetic purchase-order data. It is not connected to any employer system and contains no real company data.

## Current status
- Phase 1: synthetic data inspected; initial schema and relationships documented.
- Next: implement the processing engine and automated validation tests.

## Demo workbook
Place `CAPEX_POC_Synthetic_Data_Pack.xlsx` in `data/input/`.

## Proposed local setup
1. Create a virtual environment.
2. Install `requirements.txt`.
3. Run the Streamlit application after the processing engine is implemented.

## Safety and accounting boundaries
- Never use real employer data without explicit company authorization.
- Never connect this POC to a company drive or upload company files to personal services without IT approval.
- PO value, invoice value, received value, paid value, committed value and capitalized cost are distinct measures.
- Capitalization eligibility and accounting treatment must come from employer-approved policy and remain reviewable by Finance.
- The included CAPEX output layout is generic and must not be represented as the employer's actual template.
