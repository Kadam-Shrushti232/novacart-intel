import pytest
from app.core.models import LoadedRecord
from app.ingestion.chunker import chunk_record, record_to_text, extract_metadata


def test_chunk_order_record():
    """Test chunking a single order record."""
    record = LoadedRecord(
        data={
            "id": "ORD-001",
            "type": "order",
            "customer_id": "CUST-A123",
            "date": "2024-01-15",
            "items": [{"name": "Mouse", "quantity": 2}],
            "total": 100.00,
            "status": "shipped",
            "shipping_address": "123 Main St",
            "warehouse": "PDX-01",
        },
        source_type="order",
    )

    chunk = chunk_record(record)

    assert chunk.record_id == "ORD-001"
    assert chunk.source_type == "order"
    assert "Order ORD-001" in chunk.text
    assert chunk.metadata["source_type"] == "order"
    assert chunk.metadata["record_id"] == "ORD-001"


def test_metadata_schema_consistency():
    """Ensure metadata schema is consistent across source types."""
    source_types = [
        ("order", {"id": "ORD-001", "type": "order", "status": "shipped"}),
        ("refund", {"id": "REF-001", "type": "refund", "status": "processed"}),
        ("support_ticket", {"id": "TKT-001", "type": "support_ticket", "status": "resolved"}),
        ("supplier_report", {"id": "SUP-001", "type": "supplier_report", "status": "approved"}),
        ("warehouse_log", {"id": "WH-001", "type": "warehouse_log", "status": None}),
    ]

    required_keys = {"source_type", "record_id", "date", "category", "status"}

    for source_type, data in source_types:
        record = LoadedRecord(data=data, source_type=source_type)
        metadata = extract_metadata(record)

        for key in required_keys:
            assert key in metadata, f"Missing key {key} in {source_type} metadata"


def test_missing_customer_id_handled():
    """Test that records without customer_id are handled gracefully."""
    record = LoadedRecord(
        data={
            "id": "ORD-006",
            "type": "order",
            "date": "2024-01-20",
            "items": [{"name": "Chair", "quantity": 1}],
            "total": 215.99,
            "status": "cancelled",
        },
        source_type="order",
    )

    chunk = chunk_record(record)

    assert "UNKNOWN" in chunk.text
    assert chunk.metadata["customer_id"] is None
