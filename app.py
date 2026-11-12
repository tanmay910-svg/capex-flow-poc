
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
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
AUDIT_FILE = PROJECT_ROOT / "data" / "audit" / "audit_log.csv"

st.set_page_config(
    page_title="CAPEX FLOW | Finance Operations",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. DESIGN SYSTEM — CAPEX FLOW
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --app-bg: #090e17;
        --sidebar-bg: #0e141f;
        --card-bg: #131a26;
        --input-bg: #0e1421;
        --border: #293345;
        --text: #ebf2fc;
        --muted: #91a1b8;
        --blue: #457dfa;
        --cyan: #38c7db;
        --green: #33c28c;
        --amber: #f2ad47;
        --red: #ef7777;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(9, 14, 23, 0.96);
    }

    [data-testid="stSidebar"] {
        background: var(--sidebar-bg);
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    .block-container {
        max-width: 1500px;
        padding: 2rem 2.4rem 3rem 2.4rem;
    }

    .brand-title {
        color: var(--text);
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.7px;
        margin-bottom: 2px;
    }

    .brand-accent {
        color: var(--blue);
    }

    .brand-subtitle {
        color: var(--muted);
        font-size: 0.65rem;
        letter-spacing: 2px;
        font-weight: 600;
    }

    .sidebar-label {
        color: var(--muted);
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-top: 2rem;
        margin-bottom: 0.8rem;
    }

    .sidebar-active {
        background: #1a2940;
        border-left: 3px solid var(--blue);
        padding: 13px 12px;
        border-radius: 8px;
        color: var(--text);
        font-size: 0.85rem;
        font-weight: 650;
    }

    .sidebar-muted {
        color: var(--muted);
        font-size: 0.78rem;
        padding: 10px 4px;
    }

    .sidebar-status {
        color: var(--muted);
        font-size: 0.75rem;
        margin: 10px 0;
    }

    .status-dot {
        color: var(--green);
        margin-right: 7px;
    }

    .sidebar-footer {
        border-top: 1px solid var(--border);
        margin-top: 2rem;
        padding-top: 1.2rem;
        color: var(--muted);
        font-size: 0.68rem;
        line-height: 1.8;
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border);
        padding-bottom: 13px;
        margin-bottom: 24px;
    }

    .breadcrumb {
        color: var(--muted);
        font-size: 0.75rem;
    }

    .demo-pill {
        color: var(--cyan);
        background: #14263b;
        border: 1px solid #23415b;
        border-radius: 5px;
        padding: 7px 11px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.7px;
    }

    .page-title {
        font-size: 1.8rem;
        color: var(--text);
        font-weight: 800;
        letter-spacing: -0.8px;
        margin-bottom: 4px;
    }

    .page-subtitle {
        color: var(--muted);
        font-size: 0.82rem;
        margin-bottom: 1.4rem;
    }

    .safety-banner {
        background: #332614;
        border: 1px solid #62451f;
        border-radius: 8px;
        padding: 13px 16px;
        color: #e0c9a1;
        font-size: 0.75rem;
        margin: 1rem 0 1.5rem 0;
    }

    .safety-banner strong {
        color: var(--amber);
        margin-right: 7px;
    }

    .section-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 18px;
    }

    .section-heading {
        color: var(--text);
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .section-number {
        color: var(--blue);
        font-size: 0.72rem;
        font-weight: 800;
        margin-right: 9px;
    }

    .section-description {
        color: var(--muted);
        font-size: 0.72rem;
        margin-bottom: 15px;
    }

    .sheet-chip {
        display: inline-block;
        background: #142638;
        color: var(--cyan);
        border: 1px solid #23415b;
        border-radius: 5px;
        padding: 5px 9px;
        margin: 3px 5px 3px 0;
        font-size: 0.65rem;
        font-weight: 600;
    }

    [data-testid="stMetric"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 17px 18px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--text);
        font-size: 1.35rem;
        font-weight: 750;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.68rem;
    }

    div.stButton > button {
        background: var(--blue);
        color: white;
        border: 1px solid var(--blue);
        border-radius: 7px;
        min-height: 42px;
        font-weight: 650;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        background: #3569df;
        border-color: #3569df;
        color: white;
    }

    div.stDownloadButton > button {
        background: #142638;
        color: var(--cyan);
        border: 1px solid #28516a;
        border-radius: 7px;
        min-height: 42px;
        font-weight: 650;
    }

    div.stDownloadButton > button:hover {
        background: #1a354d;
        color: white;
        border-color: var(--cyan);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }

    [data-testid="stFileUploader"] {
        background: var(--input-bg);
        border: 1px dashed #40516c;
        border-radius: 9px;
        padding: 12px;
    }

    [data-testid="stTextInput"] input {
        background: var(--input-bg);
        border: 1px solid var(--border);
        border-radius: 7px;
        color: var(--text);
    }

    [data-testid="stExpander"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 9px;
    }

    hr {
        border-color: var(--border);
    }

    .footer-text {
        color: var(--muted);
        font-size: 0.68rem;
        text-align: center;
        padding-top: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def format_inr(value):
    """Format values as Indian Rupees."""
    try:
        return f"₹{float(value):,.0f}"
    except (ValueError, TypeError):
        return "₹0"


def write_audit_event(**kwargs):
    """Write audit events without interrupting processing."""
    try:
        log_audit_event(**kwargs)
    except Exception as error:
        st.warning(
            "The operation completed, but audit logging failed: "
            f"{type(error).__name__}"
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


def section_heading(number, title, description=None):
    """Render a consistent section heading."""
    st.markdown(
        f"""
        <div class="section-heading">
            <span class="section-number">{number}</span>{title}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if description:
        st.markdown(
            f'<div class="section-description">{description}</div>',
            unsafe_allow_html=True,
        )


def show_validation_report(validation_result):
    """Display validation issues in a readable table."""
    report = validation_result.get("report")

    if isinstance(report, pd.DataFrame) and not report.empty:
        st.dataframe(
            report,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# 4. SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="margin-bottom:35px;">
            <div class="brand-title">
                CAPEX <span class="brand-accent">FLOW</span>
            </div>
            <div class="brand-subtitle">FINANCE OPERATIONS</div>
        </div>

        <div class="sidebar-label">WORKSPACE</div>

        <div class="sidebar-active">
            ▦ &nbsp; CAPEX Processing
        </div>

        <div class="sidebar-muted">
            ◷ &nbsp; Audit History
        </div>

        <div style="border-top:1px solid #293345;margin-top:20px;"></div>

        <div class="sidebar-label">SYSTEM STATUS</div>

        <div class="sidebar-status">
            <span class="status-dot">●</span> Application initialized
        </div>
        <div class="sidebar-status">
            <span class="status-dot">●</span> Processing engine
        </div>
        <div class="sidebar-status">
            <span class="status-dot">●</span> Excel report generator
        </div>
        <div class="sidebar-status">
            <span class="status-dot">●</span> Audit logging enabled
        </div>

        <div class="sidebar-footer">
            <strong>CAPEX FLOW / VERSION 1.0</strong><br>
            Synthetic demonstration environment
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 5. MAIN HEADER
# ============================================================

st.markdown(
    """
    <div class="topbar">
        <div class="breadcrumb">
            Workspace &nbsp; / &nbsp; CAPEX Processing
        </div>
        <div class="demo-pill">● SYNTHETIC DATA DEMO</div>
    </div>

    <div class="page-title">CAPEX Processing</div>

    <div class="page-subtitle">
        Intelligent purchase order analysis and report generation
    </div>

    <div class="safety-banner">
        <strong>⚠ DEMONSTRATION ENVIRONMENT</strong>
        Use synthetic data only. Company records require explicit IT approval.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 6. WORKBOOK UPLOAD
# ============================================================

section_heading(
    "01",
    "Workbook Upload",
    "Import the SOP workbook and its supporting worksheets.",
)

with st.container(border=True):

    st.markdown("**Drop your SOP workbook here**")

    st.caption("Excel workbook (.xlsx)")

    uploaded_file = st.file_uploader(
        "Choose your SOP workbook",
        type=["xlsx"],
        accept_multiple_files=False,
        key="sop_workbook_uploader",
        help=(
            "Required worksheets: SOP_Dump, Vendor_Master, "
            "Project_Master, CAPEX_Budget and Invoice_Receipt."
        ),
        label_visibility="collapsed",
    )

    st.markdown("**REQUIRED WORKSHEETS**")

    st.markdown(
        """
        <span class="sheet-chip">SOP_Dump</span>
        <span class="sheet-chip">Vendor_Master</span>
        <span class="sheet-chip">Project_Master</span>
        <span class="sheet-chip">CAPEX_Budget</span>
        <span class="sheet-chip">Invoice_Receipt</span>
        """,
        unsafe_allow_html=True,
    )


workbook_data = None
validation_result = None
workbook_context = None


if uploaded_file is not None:

    uploaded_bytes = uploaded_file.getvalue()

    workbook_context = hashlib.sha256(
        uploaded_bytes
    ).hexdigest()

    previous_context = st.session_state.get(
        "active_workbook_context"
    )

    if previous_context != workbook_context:

        clear_processing_state()

        st.session_state["active_workbook_context"] = (
            workbook_context
        )

    try:

        uploaded_file.seek(0)

        with st.spinner("Reading workbook and supporting sheets..."):

            workbook_data = read_capex_workbook(
                uploaded_file
            )

        st.success(
            f"Workbook loaded: {uploaded_file.name}"
        )

        file_col1, file_col2, file_col3 = st.columns(3)

        file_col1.metric(
            "File Size",
            f"{len(uploaded_bytes) / 1024:.1f} KB",
        )

        file_col2.metric(
            "PO Records",
            len(workbook_data["SOP_Dump"]),
        )

        file_col3.metric(
            "Supporting Sheets",
            "4",
        )

    except Exception as error:

        st.error(
            f"Unable to read the uploaded workbook: {error}"
        )

        workbook_data = None

else:

    st.info(
        "Upload an SOP workbook to begin the processing workflow."
    )


# ============================================================
# 7. DATA VALIDATION
# ============================================================

if workbook_data is not None:

    st.divider()

    section_heading(
        "02",
        "Data Validation",
        "Checking workbook structure, required fields and data consistency.",
    )

    try:

        with st.spinner("Validating workbook data..."):

            validation_result = validate_workbook(
                workbook_data
            )

        if validation_result["status"] == "PASSED":

            st.success(
                "✓ Workbook structure verified. "
                "All validation checks passed."
            )

        else:

            st.error(
                "Workbook validation failed. "
                "Merchant processing is disabled."
            )

            show_validation_report(validation_result)

    except Exception as error:

        st.error(
            f"Validation could not be completed: {error}"
        )

        validation_result = None


# ============================================================
# 8. MERCHANT SEARCH
# ============================================================

if (
    workbook_data is not None
    and validation_result is not None
    and validation_result["status"] == "PASSED"
):

    st.divider()

    section_heading(
        "03",
        "Merchant / Vendor Search",
        "Search for a merchant using its name.",
    )

    selected_merchant = st.text_input(
        "Merchant name",
        placeholder="Enter merchant or vendor name...",
        key="merchant_search_input",
    ).strip()

    processing_context = (
        workbook_context,
        selected_merchant.casefold(),
    )

    if (
        st.session_state.get("processed_context")
        != processing_context
    ):
        clear_processing_state()

    if selected_merchant:

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
                    "Merchant not identified. "
                    "Please check the spelling or name."
                )

            elif merchant_records.empty:

                st.warning(
                    "No purchase order records were found."
                )

            else:

                st.success(
                    f"Merchant identified: "
                    f"{merchant_details['merchant_name']}"
                )

                with st.container(border=True):

                    merchant_col1, merchant_col2, merchant_col3 = (
                        st.columns(3)
                    )

                    merchant_col1.metric(
                        "Merchant",
                        merchant_details["merchant_name"],
                    )

                    merchant_col2.metric(
                        "Vendor ID",
                        merchant_details["vendor_id"],
                    )

                    merchant_col3.metric(
                        "Matching PO Lines",
                        len(merchant_records),
                    )

                # ------------------------------------------------
                # PROCESSING
                # ------------------------------------------------

                st.divider()

                section_heading(
                    "04",
                    "CAPEX Processing",
                    "Review and process the merchant's purchase order records.",
                )

                if st.button(
                    "▶  Process Merchant CAPEX",
                    type="primary",
                    use_container_width=True,
                ):

                    clear_processing_state()

                    try:

                        with st.spinner(
                            "Processing purchase orders and financial records..."
                        ):

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
                            "CAPEX processing completed successfully."
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
                # RESULTS
                # ------------------------------------------------

                has_result = (
                    "processing_result" in st.session_state
                    and st.session_state.get("processed_context")
                    == processing_context
                )

                if has_result:

                    processing_result = (
                        st.session_state["processing_result"]
                    )

                    records = processing_result["records"]
                    summary = processing_result["summary"]

                    st.divider()

                    section_heading(
                        "05",
                        "Financial Overview",
                        "Summary of purchase order and invoice values.",
                    )

                    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

                    kpi1.metric(
                        "Total PO Value",
                        format_inr(
                            summary["total_po_value_inr"]
                        ),
                    )

                    kpi2.metric(
                        "Invoice Value",
                        format_inr(
                            summary["total_invoice_value_inr"]
                        ),
                    )

                    kpi3.metric(
                        "Approved Commitment",
                        format_inr(
                            summary["approved_commitment_inr"]
                        ),
                    )

                    kpi4.metric(
                        "Records Requiring Review",
                        summary["records_requiring_review"],
                    )

                    st.caption(
                        "Approved commitment is a demonstration calculation "
                        "based on the configured approval status. "
                        "It is not a final accounting or capitalization decision."
                    )

                    # --------------------------------------------
                    # PURCHASE ORDER TABLE
                    # --------------------------------------------

                    st.divider()

                    section_heading(
                        "06",
                        "Purchase Order Details",
                        "Processed purchase order lines for the selected merchant.",
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

                    available_columns = [
                        col for col in display_columns
                        if col in records.columns
                    ]

                    st.dataframe(
                        records[available_columns],
                        use_container_width=True,
                        hide_index=True,
                    )

                    # --------------------------------------------
                    # FINANCE REVIEW
                    # --------------------------------------------

                    st.divider()

                    section_heading(
                        "07",
                        "Finance Review",
                        "Records that need additional attention before Finance approval.",
                    )

                    review_records = records[
                        records["Review_Flag"]
                        != "READY_FOR_FINANCE_REVIEW"
                    ]

                    if review_records.empty:

                        st.success(
                            "✓ No additional review flags were generated."
                        )

                    else:

                        st.warning(
                            f"{len(review_records)} records require review."
                        )

                        review_columns = [
                            "PO_Number",
                            "Project_Code",
                            "PO_Line_Total_INR",
                            "Review_Flag",
                        ]

                        available_review_columns = [
                            col for col in review_columns
                            if col in review_records.columns
                        ]

                        st.dataframe(
                            review_records[
                                available_review_columns
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )

                    # --------------------------------------------
                    # EXCEL REPORT
                    # --------------------------------------------

                    st.divider()

                    section_heading(
                        "08",
                        "Generate CAPEX Report",
                        "Create an Excel report using the configured output template.",
                    )

                    if st.button(
                        "Generate Excel Report",
                        type="primary",
                        use_container_width=True,
                    ):

                        st.session_state.pop(
                            "excel_bytes", None
                        )

                        st.session_state.pop(
                            "excel_filename", None
                        )

                        try:

                            with st.spinner(
                                "Generating CAPEX Excel report..."
                            ):

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
                                "Excel report generated successfully."
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

                    if (
                        "excel_bytes" in st.session_state
                        and "excel_filename" in st.session_state
                    ):

                        st.download_button(
                            label="⬇  Download CAPEX Excel Report",
                            data=st.session_state["excel_bytes"],
                            file_name=st.session_state[
                                "excel_filename"
                            ],
                            mime=(
                                "application/vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            use_container_width=True,
                        )

    else:

        st.info(
            "Enter a merchant name above to search the uploaded workbook."
        )


# ============================================================
# 9. AUDIT HISTORY
# ============================================================

st.divider()

section_heading(
    "09",
    "Audit History",
    "Operational events recorded by the local demonstration application.",
)

with st.expander("View Audit Log"):

    if AUDIT_FILE.exists():

        try:

            audit_data = pd.read_csv(AUDIT_FILE)

            if audit_data.empty:

                st.info("No audit events have been recorded yet.")

            else:

                st.dataframe(
                    audit_data,
                    use_container_width=True,
                    hide_index=True,
                )

            st.caption(
                "The local demonstration log records operational metadata. "
                "Production deployment requires centralized, access-controlled "
                "and tamper-protected audit logging."
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
# 10. FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer-text">
        CAPEX FLOW &nbsp; | &nbsp; FINANCE OPERATIONS
        <br>
        Configurable Excel Input &nbsp; • &nbsp;
        Synthetic Demonstration Environment
    </div>
    """,
    unsafe_allow_html=True,
)
