import json
from pathlib import Path
from typing import Generator
from app.core.models import LoadedRecord


SOURCE_FILES = {
    "order": "data/synthetic/orders.json",
    "refund": "data/synthetic/refunds.json",
    "support_ticket": "data/synthetic/support_tickets.json",
    "supplier_report": "data/synthetic/supplier_reports.json",
    "warehouse_log": "data/synthetic/warehouse_logs.json",
}


def load_records(data_dir: str = ".") -> Generator[LoadedRecord, None, None]:
    """
    Load all records from the synthetic dataset files.

    Yields individual records from each source type, not file-level documents.
    Each record gets tagged with its source type for metadata filtering.
    """
    base_path = Path(data_dir)

    for source_type, file_path in SOURCE_FILES.items():
        full_path = base_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"Data file not found: {full_path}")

        with open(full_path, "r") as f:
            records = json.load(f)

        for record in records:
            yield LoadedRecord(data=record, source_type=source_type)
