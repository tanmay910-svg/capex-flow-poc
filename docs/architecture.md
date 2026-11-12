# CAPEX Automation POC — architecture

```text
Synthetic Excel workbook / later IT-approved source
                     |
                     v
             Input / schema reader
                     |
                     v
             Data quality validator
                     |
                     v
       Merchant resolver (name -> Vendor_ID)
                     |
                     v
        PO-line selection and enrichment
           |          |          |
        Vendor      Project    Budget
           |          |          |
           +------ Invoice/receipt aggregation
                     |
                     v
          CAPEX review / exception engine
                     |
                     v
        Copy of configured Excel template
                     |
                     v
          Output workbook + validation log
```

## Proposed modules
- `src/excel_reader.py`: read workbook sheets and headers.
- `src/validator.py`: schema, key, relationship and amount checks.
- `src/merchant_matcher.py`: resolve merchant input to vendor ID.
- `src/capex_processor.py`: filter, enrich and aggregate PO lines.
- `src/excel_generator.py`: populate a copy of the template.
- `app.py`: Streamlit user interface.

## Production boundary
The POC runs locally on synthetic data. Production access to SharePoint, OneDrive, network drives or finance systems is a separate IT-approved deployment/integration task. Authentication, least-privilege access, audit logging, retention, encryption, and approved hosting must be designed with the employer's IT/security team.

## Public reference points used for the POC design
- IFRS Foundation, IAS 16: recognition of PPE depends on probable future economic benefits and reliable measurement; cost can include purchase price and directly attributable costs. This supports keeping CAPEX eligibility and accounting policy as explicit, employer-approved rules rather than guessing from a PO. https://www.ifrs.org/issued-standards/list-of-standards/ias-16-property-plant-and-equipment/
- Microsoft Support, Power Query folder import: combining files is simplest when files share a consistent schema, headers and data types; the same general approach supports SharePoint folders. https://support.microsoft.com/en-us/excel/import-data-from-data-sources-power-query
- Microsoft Learn, Excel Online (Business) connector: the connector works with OneDrive for Business and SharePoint document libraries, but documents limitations around filtering, concurrent modifications, file size and throttling. These should be reviewed if a later implementation uses Power Automate. https://learn.microsoft.com/en-us/connectors/excelonlinebusiness/
