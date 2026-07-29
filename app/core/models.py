from typing import Optional, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pydantic import BaseModel, Field


@dataclass
class Chunk:
    """A single indexed document chunk with metadata for retrieval."""
    text: str
    metadata: dict[str, Any]
    source_type: str
    record_id: str


@dataclass
class LoadedRecord:
    """A raw record loaded from a JSON source file."""
    data: dict
    source_type: str


class ChatRequest(BaseModel):
    """Request body for POST /chat endpoint."""
    question: str = Field(..., min_length=1, description="The question to answer")


class ToolCall(BaseModel):
    """A single tool call executed by the agent."""
    tool_name: str
    tool_input: dict
    result: str


class ChatResponse(BaseModel):
    """Response from POST /chat endpoint."""
    answer: str
    citations: List[str]
    tool_calls: List[ToolCall]
    model_used: str


class DocumentUploadRequest(BaseModel):
    """Request body for POST /documents/upload endpoint."""
    source_type: str = Field(..., description="One of: order, refund, support_ticket, supplier_report, warehouse_log")
    data: dict = Field(..., description="The document data matching the source_type schema")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None
