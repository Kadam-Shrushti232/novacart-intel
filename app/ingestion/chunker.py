import json
from typing import Optional
from app.core.models import LoadedRecord, Chunk


def record_to_text(record: LoadedRecord) -> str:
    """Convert a structured record to clean natural-language text for embedding."""
    data = record.data
    source_type = record.source_type

    if source_type == "order":
        items_desc = "; ".join(
            [f"{item['name']} (qty {item['quantity']})" for item in data.get("items", [])]
        )
        return (
            f"Order {data['id']} from {data.get('date', 'unknown date')}. "
            f"Customer {data.get('customer_id', 'UNKNOWN')}. "
            f"Items: {items_desc}. "
            f"Total: ${data.get('total', 'unknown')}. "
            f"Status: {data.get('status', 'unknown')}. "
            f"Shipping to {data.get('shipping_address', 'unknown')} from warehouse {data.get('warehouse', 'unknown')}."
        )

    elif source_type == "refund":
        items_desc = "; ".join(
            [f"{item['name']} (qty {item['quantity']})" for item in data.get("items_refunded", [])]
        )
        return (
            f"Refund {data['id']} for order {data.get('order_id', 'unknown')} from {data.get('date', 'unknown date')}. "
            f"Customer {data.get('customer_id', 'UNKNOWN')}. "
            f"Reason: {data.get('reason', 'not specified')}. "
            f"Items: {items_desc}. "
            f"Refund amount: ${data.get('total_refund', 'unknown')}. "
            f"Status: {data.get('status', 'unknown')}. "
            f"Method: {data.get('method', 'unknown')}. "
            f"Policy version: {data.get('policy_version', 'current')}."
        )

    elif source_type == "support_ticket":
        return (
            f"Support ticket {data['id']} opened {data.get('date_opened', 'unknown date')}. "
            f"Customer {data.get('customer_id', 'UNKNOWN')}. "
            f"Subject: {data.get('subject', 'no subject')}. "
            f"Priority: {data.get('priority', 'unknown')}. "
            f"Category: {data.get('category', 'general')}. "
            f"Status: {data.get('status', 'unknown')}. "
            f"Description: {data.get('description', 'none')}. "
            f"Resolution: {data.get('resolution', 'pending')}. "
            f"Assigned to {data.get('assigned_to', 'unassigned')}."
        )

    elif source_type == "supplier_report":
        defects = "; ".join(data.get("defect_types", []))
        return (
            f"Supplier quality report {data['id']} from {data.get('report_date', 'unknown date')}. "
            f"Supplier: {data.get('supplier_name', 'unknown')}. "
            f"Product: {data.get('product_name', 'unknown')} (SKU {data.get('product_sku', 'unknown')}). "
            f"Batch {data.get('batch_id', 'unknown')}. "
            f"Inspected: {data.get('units_inspected', 0)} units. "
            f"Passed: {data.get('units_passed', 0)}, Failed: {data.get('units_failed', 0)}. "
            f"Defect rate: {data.get('defect_rate', 'unknown')}. "
            f"Defects: {defects}. "
            f"Action: {data.get('action_taken', 'none')}. "
            f"Status: {data.get('status', 'unknown')}."
        )

    elif source_type == "warehouse_log":
        return (
            f"Warehouse log {data['id']} from {data.get('date', 'unknown date')} at {data.get('time', 'unknown time')}. "
            f"Warehouse: {data.get('warehouse_name', 'unknown')} ({data.get('warehouse_id', 'unknown')}). "
            f"Event: {data.get('event_type', 'unknown')}. "
            f"Order: {data.get('order_id', data.get('supplier', 'N/A'))}. "
            f"Details: {json.dumps({k: v for k, v in data.items() if k not in ['id', 'type', 'date', 'time', 'warehouse_name', 'warehouse_id', 'event_type', 'order_id', 'supplier']}, default=str)}."
        )

    return json.dumps(data)


def extract_metadata(record: LoadedRecord) -> dict:
    """Extract a consistent metadata schema from any record type.
    Includes date_int (YYYYMMDD integer) for proper Chroma range filtering.
    """
    data = record.data
    source_type = record.source_type

    # Extract date string from the appropriate field
    date_str = data.get("date", data.get("date_opened", data.get("report_date")))

    # Convert date string to YYYYMMDD integer for Chroma $gte/$lte operators
    date_int = None
    if date_str:
        try:
            # Expected format: YYYY-MM-DD
            date_int = int(date_str.replace("-", ""))
        except (ValueError, AttributeError):
            date_int = None

    metadata = {
        "source_type": source_type,
        "record_id": data.get("id", "unknown"),
        "date": date_str,
        "date_int": date_int,
        "category": None,
        "status": data.get("status", None),
    }

    if source_type == "order":
        metadata["category"] = "order"
        metadata["warehouse"] = data.get("warehouse")
        metadata["customer_id"] = data.get("customer_id")

    elif source_type == "refund":
        metadata["category"] = "refund"
        metadata["order_id"] = data.get("order_id")
        metadata["reason"] = data.get("reason")
        metadata["customer_id"] = data.get("customer_id")
        metadata["policy_version"] = data.get("policy_version")

    elif source_type == "support_ticket":
        metadata["category"] = data.get("category", "general")
        metadata["priority"] = data.get("priority")
        metadata["customer_id"] = data.get("customer_id")

    elif source_type == "supplier_report":
        metadata["category"] = "supplier_quality"
        metadata["supplier_name"] = data.get("supplier_name")
        metadata["product_sku"] = data.get("product_sku")
        metadata["defect_rate"] = data.get("defect_rate")
        metadata["batch_id"] = data.get("batch_id")

    elif source_type == "warehouse_log":
        metadata["category"] = data.get("event_type", "warehouse")
        metadata["warehouse_id"] = data.get("warehouse_id")
        metadata["order_id"] = data.get("order_id")

    return metadata


def chunk_record(record: LoadedRecord) -> Chunk:
    """Convert a single record into a chunk with text and metadata."""
    text = record_to_text(record)
    metadata = extract_metadata(record)

    return Chunk(
        text=text,
        metadata=metadata,
        source_type=record.source_type,
        record_id=metadata["record_id"],
    )
