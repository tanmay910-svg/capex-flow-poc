
from pathlib import Path
from datetime import datetime
import csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit_log.csv"

AUDIT_COLUMNS = [
    "Timestamp",
    "Event_Type",
    "Merchant_Name",
    "Vendor_ID",
    "Record_Count",
    "Status",
    "Output_Filename",
    "Error_Type",
]


def log_audit_event(
    event_type,
    merchant_name=None,
    vendor_id=None,
    record_count=None,
    status="SUCCESS",
    output_filename=None,
    error_type=None,
):
    """
    Append one event to the CAPEX audit log.

    Only operational metadata is recorded.
    Financial transaction values are intentionally excluded.
    """

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    event = {
        "Timestamp": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "Event_Type": event_type,
        "Merchant_Name": merchant_name,
        "Vendor_ID": vendor_id,
        "Record_Count": record_count,
        "Status": status,
        "Output_Filename": output_filename,
        "Error_Type": error_type,
    }

    file_exists = AUDIT_FILE.exists()

    with AUDIT_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=AUDIT_COLUMNS,
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(event)

    return AUDIT_FILE

