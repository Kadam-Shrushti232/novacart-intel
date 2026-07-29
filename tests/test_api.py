"""Tests for FastAPI endpoints (Phase 6)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock


client = TestClient(app)


class TestHealthEndpoint:
    """Test /health endpoint - no auth required."""

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestRootEndpoint:
    """Test root / endpoint."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["name"] == "NovaCart Intelligence Layer"


class TestChatEndpoint:
    """Test POST /chat endpoint."""

    def test_chat_requires_api_key(self):
        """POST /chat without X-API-Key returns 401."""
        response = client.post("/chat", json={"question": "What happened?"})
        assert response.status_code == 401

    def test_chat_with_invalid_api_key(self):
        """POST /chat with invalid X-API-Key returns 403."""
        response = client.post(
            "/chat",
            json={"question": "What happened?"},
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 403

    @patch("app.main.RetrievalAgent")
    @patch("app.core.auth.get_settings")
    def test_chat_with_valid_api_key(self, mock_settings, mock_agent_class):
        """POST /chat with valid X-API-Key returns 200."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_agent = MagicMock()
        mock_agent.ask.return_value = MagicMock(
            final_answer="Test answer",
            cited_records=["ORD-001"],
            tool_calls=[{
                "tool_name": "search_orders",
                "tool_input": {"query": "orders"},
                "result": "Order results"
            }],
            model_used="test-model"
        )
        mock_agent_class.return_value = mock_agent

        response = client.post(
            "/chat",
            json={"question": "What happened?"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Test answer"
        assert body["citations"] == ["ORD-001"]
        assert body["model_used"] == "test-model"
        assert len(body["tool_calls"]) == 1

    @patch("app.main.RetrievalAgent")
    @patch("app.core.auth.get_settings")
    def test_chat_handles_api_key_missing_error(self, mock_settings, mock_agent_class):
        """POST /chat handles missing OPENROUTER_API_KEY."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_agent_class.side_effect = ValueError("OPENROUTER_API_KEY not set")

        response = client.post(
            "/chat",
            json={"question": "What happened?"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 503
        assert "OpenRouter API key not configured" in response.json()["detail"]

    @patch("app.main.RetrievalAgent")
    @patch("app.core.auth.get_settings")
    def test_chat_handles_rate_limit(self, mock_settings, mock_agent_class):
        """POST /chat handles rate limit errors."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_agent_class.side_effect = Exception("429 Rate limited")

        response = client.post(
            "/chat",
            json={"question": "What happened?"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 429
        assert "rate limited" in response.json()["detail"]

    @patch("app.main.RetrievalAgent")
    @patch("app.core.auth.get_settings")
    def test_chat_handles_connection_error(self, mock_settings, mock_agent_class):
        """POST /chat handles connection errors."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_agent_class.side_effect = Exception("Connection timeout")

        response = client.post(
            "/chat",
            json={"question": "What happened?"},
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 502


class TestDocumentUploadEndpoint:
    """Test POST /documents/upload endpoint."""

    def test_upload_requires_api_key(self):
        """POST /documents/upload without X-API-Key returns 401."""
        response = client.post(
            "/documents/upload",
            json={"source_type": "order", "data": {}}
        )
        assert response.status_code == 401

    @patch("app.core.auth.get_settings")
    def test_upload_malformed_order_missing_fields(self, mock_settings):
        """POST /documents/upload with missing required fields returns 400."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        response = client.post(
            "/documents/upload",
            json={
                "source_type": "order",
                "data": {
                    "id": "ORD-001",
                }
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]

    @patch("app.core.auth.get_settings")
    def test_upload_invalid_source_type(self, mock_settings):
        """POST /documents/upload with invalid source_type returns 400."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        response = client.post(
            "/documents/upload",
            json={
                "source_type": "invalid_type",
                "data": {"id": "TEST-001"}
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 400
        assert "Invalid source_type" in response.json()["detail"]

    @patch("app.main.index_chunks")
    @patch("app.main.embed_text")
    @patch("app.core.auth.get_settings")
    def test_upload_valid_order(self, mock_settings, mock_embed, mock_index):
        """POST /documents/upload with valid order returns 201."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_index.return_value = 1

        response = client.post(
            "/documents/upload",
            json={
                "source_type": "order",
                "data": {
                    "id": "ORD-001",
                    "date": "2024-01-15",
                    "customer_id": "CUST-A123",
                    "items": [{"name": "Mouse", "quantity": 2}],
                    "total": 100.0,
                    "status": "shipped",
                    "shipping_address": "123 Main St",
                    "warehouse": "PDX-01"
                }
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "success"
        assert body["record_id"] == "ORD-001"
        assert body["indexed"] == 1

    @patch("app.main.index_chunks")
    @patch("app.main.embed_text")
    @patch("app.core.auth.get_settings")
    def test_upload_handles_embedding_error(self, mock_settings, mock_embed, mock_index):
        """POST /documents/upload handles embedding errors."""
        mock_settings_instance = MagicMock()
        mock_settings_instance.api_key = "test-api-key"
        mock_settings.return_value = mock_settings_instance

        mock_embed.side_effect = Exception("Embedding service down")

        response = client.post(
            "/documents/upload",
            json={
                "source_type": "refund",
                "data": {
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
            },
            headers={"X-API-Key": "test-api-key"}
        )
        assert response.status_code == 500
        assert "Failed to index document" in response.json()["detail"]
