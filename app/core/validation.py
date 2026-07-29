"""Validation for document uploads by source type."""

from typing import Optional


REQUIRED_FIELDS = {
    "order": ["id", "date", "customer_id", "items", "total", "status", "shipping_address", "warehouse"],
    "refund": ["id", "order_id", "date", "customer_id", "reason", "items_refunded", "total_refund", "status", "method"],
    "support_ticket": ["id", "date_opened", "customer_id", "subject", "priority", "category", "status"],
    "supplier_report": ["id", "report_date", "supplier_name", "product_name", "product_sku", "batch_id", "units_inspected", "units_passed", "units_failed", "status"],
    "warehouse_log": ["id", "date", "time", "warehouse_name", "warehouse_id", "event_type"],
}


def validate_document(source_type: str, data: dict) -> tuple[bool, Optional[str]]:
    """Validate that a document has all required fields for its source_type.

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
    """
    if source_type not in REQUIRED_FIELDS:
        return False, f"Invalid source_type: {source_type}. Must be one of: {', '.join(REQUIRED_FIELDS.keys())}"

    required = REQUIRED_FIELDS[source_type]
    missing = [field for field in required if field not in data]

    if missing:
        return False, f"Missing required fields for {source_type}: {', '.join(missing)}"

    return True, None
