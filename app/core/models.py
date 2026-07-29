from typing import Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


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
