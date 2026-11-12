
from pathlib import Path
import hashlib

import streamlit as st
import pandas as pd

from src.excel_reader import read_capex_workbook
from src.validator import validate_workbook
from src.merchant_matcher import search_merchant
from src.capex_processor import process_merchant_capex
from src.excel_generator import generate_capex_excel
from src.audit_logger import log_audit_event


# ============================================================
# 1. APPLICATION CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
AUDIT_FILE = PROJECT_ROOT / "data" / "audit" / "audit_log.csv"

st.set_page_config(
    page_title="CAPEX Automation Portal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: var(--text-color);
        letter-spacing: -0.8px;
        margin-bottom: 0.35rem;
    }

    .sub-title {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 1rem;
        margin-bottom: 1rem;
    }

    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        padding: 1.2rem;
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.65rem;
        font-weight: 750;
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 650;
        min-height: 2.8rem;
    }

    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def format_inr(value):
    """Format a numeric value as Indian Rupees."""
    return f"₹{float(value):,.0f}"


def write_audit_event(**kwargs):
    """Write an audit event without interrupting the workflow."""
    try:
        log_audit_event(**kwargs)
    except Exception as audit_error:
        st.warning(
            "Operation completed, but audit logging failed: "
            f"{type(audit_error).__name__}"
        )


def clear_processing_state():
    """Clear previous processing and download results."""

    keys = [
        "processing_result",
        "processed_merchant",
        "processed_context",
        "excel_bytes",
        "excel_filename",
    ]

    for key in keys:
        st.session_state.pop(key, None)


# ============================================================
# 4. APPLICATION HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📊 CAPEX Automation Portal</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">'
    'Purchase Order Processing and CAPEX Report Generation'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()

st.warning(
    "PROOF OF CONCEPT — Use fictional or synthetic data for "
    "demonstrations. Do not upload company or confidential "
    "financial records before receiving IT approval."
)


# ============================================================
# 5. SIDEBAR — SYSTEM INFORMATION
# ============================================================

st.sidebar.title("System Status")

st.sidebar.info("Waiting for workbook upload")

st.sidebar.divider()

st.sidebar.caption(
    "CAPEX Automation POC | Configurable Excel Input"
)


# ============================================================
# 6. WORKBOOK UPLOAD
# ============================================================

st.subheader("1. Upload SOP Workbook")

st.write(
    "Upload the Excel workbook containing the SOP dump "
    "and its supporting worksheets."
)

uploaded_file = st.file_uploader(
    "Choose an SOP workbook",
    type=["xlsx"],
    accept_multiple_files=False,
    help=(
        "The workbook must contain SOP_Dump, Vendor_Master, "
        "Project_Master, CAPEX_Budget and Invoice_Receipt."
    ),
    key="sop_workbook_uploader",
)


workbook_data = None
validation_result = None
workbook_context = None


if uploaded_file is not None:

    uploaded_bytes = uploaded_file.getvalue()

    file_hash = hashlib.sha256(
        uploaded_bytes
    ).hexdigest()

    workbook_context = file_hash

    # Clear results if a different workbook is uploaded.
    previous_context = st.session_state.get(
        "active_workbook_context"
    )

    if previous_context != workbook_context:

        clear_processing_state()

        st.session_state["active_workbook_context"] = (
            workbook_context
        )

    st.success(
        f"Workbook selected: {uploaded_file.name}"
    )

    st.caption(
        f"File size: {len(uploaded_bytes) / 1024:.1f} KB"
    )

    # --------------------------------------------------------
    # READ WORKBOOK
    # --------------------------------------------------------

    try:
        uploaded_file.seek(0)

        with st.spinner("Reading uploaded Excel workbook..."):

            workbook_data = read_capex_workbook(
                uploaded_file
            )

        st.success("All required worksheets loaded successfully.")

    except Exception as error:

        st.error(
            f"Unable to read uploaded workbook: {error}"
        )

        workbook_data = None


# ============================================================
# 7. WORKBOOK VALIDATION
# ============================================================

if workbook_data is not None:

    st.subheader("2. Workbook Validation")

    try:

        validation_result = validate_workbook(
            workbook_data
        )

        if validation_result["status"] == "PASSED":

            st.success(
                "Workbook validation completed successfully."
            )

        else:

            st.error(
                "Workbook validation failed. "
                "CAPEX processing is disabled."
            )

            st.dataframe(
                validation_result["report"],
                width="stretch",
                hide_index=True,
            )

    except Exception as error:

        st.error(
            f"Workbook validation could not be completed: {error}"
        )

        validation_result = None


# ============================================================
# 8. SIDEBAR — UPLOADED WORKBOOK STATUS
# ============================================================

if workbook_data is not None:

    st.sidebar.success("Workbook Loaded")

    if validation_result is not None:

        if validation_result["status"] == "PASSED":
            st.sidebar.success("Validation: PASSED")
        else:
            st.sidebar.error("Validation: FAILED")

    st.sidebar.write(
        f"**PO Records:** {len(workbook_data['SOP_Dump'])}"
    )

    st.sidebar.write(
        f"**Vendors:** {len(workbook_data['Vendor_Master'])}"
    )

    st.sidebar.write(
        f"**Projects:** {len(workbook_data['Project_Master'])}"
    )

    st.sidebar.write(
        f"**Invoices:** {len(workbook_data['Invoice_Receipt'])}"
    )


# ============================================================
# 9. MERCHANT SEARCH
# ============================================================

if (
    workbook_data is not None
    and validation_result is not None
    and validation_result["status"] == "PASSED"
):

    st.divider()

    st.subheader("3. Merchant / Vendor Search")

    selected_merchant = st.text_input(
        "Enter merchant or vendor name",
        placeholder="Example: ABC Technologies",
        help=(
            "Enter the merchant name as it appears in "
            "the uploaded workbook."
        ),
        key="merchant_search_input",
    ).strip()

    # Context includes both workbook and merchant.
    processing_context = (
        workbook_context,
        selected_merchant.casefold()
    )

    # Clear old output if merchant changes.
    if (
        st.session_state.get("processed_context")
        != processing_context
    ):
        clear_processing_state()

    if selected_merchant:

        # ----------------------------------------------------
        # MERCHANT MATCHING
        # ----------------------------------------------------

        try:

            merchant_result = search_merchant(
                workbook_data,
                selected_merchant,
            )

            merchant_details = merchant_result["merchant"]
            merchant_records = merchant_result["records"]

        except Exception as error:

            st.error(
                f"Merchant search failed: {error}"
            )

            merchant_result = None

        if merchant_result is not None:

            if merchant_details["status"] != "FOUND":

                st.error(
                    "Merchant could not be identified. "
                    "Check the spelling or merchant name."
                )

            elif merchant_records.empty:

                st.warning(
                    "No purchase order records were found "
                    "for this merchant."
                )

            else:

                st.success(
                    f"Merchant identified: "
                    f"{merchant_details['merchant_name']}"
                )

                # ------------------------------------------------
                # MERCHANT INFORMATION
                # ------------------------------------------------

                st.subheader("4. Merchant Information")

                info1, info2, info3 = st.columns(3)

                info1.metric(
                    "Merchant Name",
                    merchant_details["merchant_name"],
                )

                info2.metric(
                    "Vendor ID",
                    merchant_details["vendor_id"],
                )

                info3.metric(
                    "Matching PO Lines",
                    len(merchant_records),
                )

                # ------------------------------------------------
                # CAPEX PROCESSING
                # ------------------------------------------------

                st.subheader("5. CAPEX Processing")

                if st.button(
                    "Process Merchant CAPEX",
                    type="primary",
                    width="stretch",
                ):

                    clear_processing_state()

                    with st.spinner(
                        "Processing purchase orders and financial records..."
                    ):

                        try:

                            processing_result = (
                                process_merchant_capex(
                                    workbook_data,
                                    merchant_result,
                                )
                            )

                            st.session_state[
                                "processing_result"
                            ] = processing_result

                            st.session_state[
                                "processed_merchant"
                            ] = merchant_details["merchant_name"]

                            st.session_state[
                                "processed_context"
                            ] = processing_context

                            write_audit_event(
                                event_type="CAPEX_PROCESSING",
                                merchant_name=(
                                    merchant_details["merchant_name"]
                                ),
                                vendor_id=merchant_details["vendor_id"],
                                record_count=len(
                                    processing_result["records"]
                                ),
                                status="SUCCESS",
                            )

                            st.success(
                                "CAPEX processing completed!"
                            )

                        except Exception as error:

                            write_audit_event(
                                event_type="CAPEX_PROCESSING",
                                merchant_name=(
                                    merchant_details["merchant_name"]
                                ),
                                vendor_id=merchant_details["vendor_id"],
                                status="FAILED",
                                error_type=type(error).__name__,
                            )

                            st.error(
                                f"Processing failed: {error}"
                            )

                # ------------------------------------------------
                # DISPLAY PROCESSED RESULTS
                # ------------------------------------------------

                has_result = (
                    "processing_result" in st.session_state
                    and st.session_state.get(
                        "processed_context"
                    ) == processing_context
                )

                if has_result:

                    processing_result = (
                        st.session_state["processing_result"]
                    )

                    records = processing_result["records"]
                    summary = processing_result["summary"]

                    st.success(
                        "CAPEX processing completed successfully!"
                    )

                    # --------------------------------------------
                    # FINANCIAL SUMMARY
                    # --------------------------------------------

                    st.subheader("6. Financial Summary")

                    col1, col2, col3, col4 = st.columns(4)

                    col1.metric(
                        "Total PO Value",
                        format_inr(
                            summary["total_po_value_inr"]
                        ),
                    )

                    col2.metric(
                        "Invoice Value",
                        format_inr(
                            summary["total_invoice_value_inr"]
                        ),
                    )

                    col3.metric(
                        "Approved Commitment",
                        format_inr(
                            summary["approved_commitment_inr"]
                        ),
                    )

                    col4.metric(
                        "Records Requiring Review",
                        summary["records_requiring_review"],
                    )

                    st.divider()

                    # --------------------------------------------
                    # PROCESSED PURCHASE ORDERS
                    # --------------------------------------------

                    st.subheader(
                        "7. Processed Purchase Orders"
                    )

                    display_columns = [
                        "PO_Number",
                        "PO_Line_No",
                        "Project_Code",
                        "Item_Description",
                        "PO_Line_Total_INR",
                        "Invoice_Amount_INR",
                        "Approval_Status",
                        "Receipt_Status",
                        "Review_Flag",
                    ]

                    st.dataframe(
                        records[display_columns],
                        width="stretch",
                        hide_index=True,
                    )

                    # --------------------------------------------
                    # FINANCE REVIEW
                    # --------------------------------------------

                    st.subheader("8. Finance Review")

                    review_records = records[
                        records["Review_Flag"]
                        != "READY_FOR_FINANCE_REVIEW"
                    ]

                    if review_records.empty:

                        st.success(
                            "No records require additional review."
                        )

                    else:

                        st.warning(
                            f"{len(review_records)} records "
                            "require Finance review."
                        )

                        review_columns = [
                            "PO_Number",
                            "Project_Code",
                            "PO_Line_Total_INR",
                            "Review_Flag",
                        ]

                        st.dataframe(
                            review_records[review_columns],
                            width="stretch",
                            hide_index=True,
                        )

                    # --------------------------------------------
                    # EXCEL REPORT GENERATION
                    # --------------------------------------------

                    st.divider()

                    st.subheader(
                        "9. Generate CAPEX Excel Report"
                    )

                    if st.button(
                        "Generate Excel Report",
                        type="primary",
                        width="stretch",
                    ):

                        st.session_state.pop(
                            "excel_bytes", None
                        )

                        st.session_state.pop(
                            "excel_filename", None
                        )

                        try:

                            output_path = generate_capex_excel(
                                processed_records=records,
                                merchant_name=(
                                    merchant_details["merchant_name"]
                                ),
                            )

                            with open(
                                output_path,
                                "rb"
                            ) as excel_file:

                                excel_bytes = excel_file.read()

                            st.session_state[
                                "excel_bytes"
                            ] = excel_bytes

                            st.session_state[
                                "excel_filename"
                            ] = output_path.name

                            write_audit_event(
                                event_type="EXCEL_REPORT_GENERATION",
                                merchant_name=(
                                    merchant_details["merchant_name"]
                                ),
                                vendor_id=merchant_details["vendor_id"],
                                record_count=len(records),
                                status="SUCCESS",
                                output_filename=output_path.name,
                            )

                            st.success(
                                "CAPEX Excel report generated successfully!"
                            )

                        except Exception as error:

                            write_audit_event(
                                event_type="EXCEL_REPORT_GENERATION",
                                merchant_name=(
                                    merchant_details["merchant_name"]
                                ),
                                vendor_id=merchant_details["vendor_id"],
                                status="FAILED",
                                error_type=type(error).__name__,
                            )

                            st.error(
                                f"Excel generation failed: {error}"
                            )

                    # --------------------------------------------
                    # DOWNLOAD REPORT
                    # --------------------------------------------

                    if (
                        "excel_bytes" in st.session_state
                        and "excel_filename" in st.session_state
                    ):

                        st.download_button(
                            label="⬇ Download CAPEX Excel Report",
                            data=st.session_state["excel_bytes"],
                            file_name=st.session_state[
                                "excel_filename"
                            ],
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            width="stretch",
                        )

    else:

        st.info(
            "Enter a merchant name to search the uploaded workbook."
        )


elif uploaded_file is None:

    st.info(
        "Upload an SOP workbook above to begin CAPEX processing."
    )


# ============================================================
# 10. AUDIT LOG VIEWER
# ============================================================

st.divider()

with st.expander("View System Audit Log"):

    if AUDIT_FILE.exists():

        try:

            audit_data = pd.read_csv(AUDIT_FILE)

            st.dataframe(
                audit_data,
                width="stretch",
                hide_index=True,
            )

            st.caption(
                "The local demonstration log records operational "
                "metadata, not transaction-level financial details."
            )

        except Exception as error:

            st.error(
                f"Unable to read audit log: {error}"
            )

    else:

        st.info(
            "No audit events have been recorded yet."
        )


# ============================================================
# 11. FOOTER
# ============================================================

st.divider()

st.caption(
    "CAPEX Automation POC | Configurable Excel Input | "
    "For demonstration purposes only"
)
