"""Tests for document validation (Phase 6)."""

import pytest
from app.core.validation import validate_document


class TestDocumentValidation:
    """Test document validation by source type."""

    def test_validate_order_all_required_fields(self):
        """Valid order with all required fields."""
        data = {
            "id": "ORD-001",
            "date": "2024-01-15",
            "customer_id": "CUST-A123",
            "items": [{"name": "Mouse", "quantity": 2}],
            "total": 100.0,
            "status": "shipped",
            "shipping_address": "123 Main St",
            "warehouse": "PDX-01"
        }
        is_valid, error = validate_document("order", data)
        assert is_valid is True
        assert error is None

    def test_validate_order_missing_field(self):
        """Order missing required field."""
        data = {
            "id": "ORD-001",
            "date": "2024-01-15",
            # Missing customer_id
            "items": [{"name": "Mouse", "quantity": 2}],
            "total": 100.0,
            "status": "shipped",
            "shipping_address": "123 Main St",
            "warehouse": "PDX-01"
        }
        is_valid, error = validate_document("order", data)
        assert is_valid is False
        assert "customer_id" in error

    def test_validate_refund_all_required_fields(self):
        """Valid refund with all required fields."""
        data = {
            "id": "REF-001",
            "order_id": "ORD-001",
            "date": "2024-01-20",
            "customer_id": "CUST-B456",
            "reason": "Wrong item",
            "items_refunded": [{"name": "Keyboard", "quantity": 1}],
            "total_refund": 97.19,
            "status": "processed",
            "method": "original_payment"
        }
        is_valid, error = validate_document("refund", data)
        assert is_valid is True
        assert error is None

    def test_validate_support_ticket_all_required_fields(self):
        """Valid support ticket with all required fields."""
        data = {
            "id": "TKT-001",
            "date_opened": "2024-01-22",
            "customer_id": "CUST-A123",
            "subject": "Mouse not responding",
            "priority": "high",
            "category": "product_defect",
            "status": "resolved"
        }
        is_valid, error = validate_document("support_ticket", data)
        assert is_valid is True
        assert error is None

    def test_validate_supplier_report_all_required_fields(self):
        """Valid supplier report with all required fields."""
        data = {
            "id": "SUP-001",
            "report_date": "2024-01-15",
            "supplier_name": "ElectroTech Manufacturing",
            "product_name": "Wireless Mouse",
            "product_sku": "SKU-4521",
            "batch_id": "BATCH-20240110-001",
            "units_inspected": 100,
            "units_passed": 99,
            "units_failed": 1,
            "status": "approved"
        }
        is_valid, error = validate_document("supplier_report", data)
        assert is_valid is True
        assert error is None

    def test_validate_warehouse_log_all_required_fields(self):
        """Valid warehouse log with all required fields."""
        data = {
            "id": "WH-001",
            "date": "2024-01-15",
            "time": "09:30:00",
            "warehouse_name": "Portland Distribution Center",
            "warehouse_id": "PDX-01",
            "event_type": "shipment_processed"
        }
        is_valid, error = validate_document("warehouse_log", data)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_source_type(self):
        """Invalid source_type."""
        data = {"id": "TEST-001"}
        is_valid, error = validate_document("invalid_type", data)
        assert is_valid is False
        assert "Invalid source_type" in error

    def test_validate_multiple_missing_fields(self):
        """Report all missing fields."""
        data = {
            "id": "ORD-001",
            # Missing: date, customer_id, items, total, status, shipping_address, warehouse
        }
        is_valid, error = validate_document("order", data)
        assert is_valid is False
        assert "date" in error
        assert "customer_id" in error
        assert "items" in error
