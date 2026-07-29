"""Tool definitions for the retrieval agent.

These are Gemini-compatible tool definitions that wrap Phase 4 semantic_search()
with source_type pre-filtering.
"""

from typing import Optional
from app.retrieval.search import semantic_search


TOOL_DEFINITIONS = [
    {
        "name": "search_orders",
        "description": "Search for order records. Use this to find information about customer orders, items purchased, totals, shipping addresses, and warehouse assignments.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about orders (e.g., 'laptop orders', 'Portland warehouse shipments')"
                },
                "date_range": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional date range as [start_date, end_date] in YYYY-MM-DD format (inclusive)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_refunds",
        "description": "Search for refund records. Use this to find information about customer refunds, reasons, amounts, policy versions, and refund methods.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about refunds (e.g., 'cancellation refunds', 'defective products')"
                },
                "date_range": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional date range as [start_date, end_date] in YYYY-MM-DD format (inclusive)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_tickets",
        "description": "Search for support ticket records. Use this to find information about customer support issues, categories, priority levels, status, and resolutions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about support issues (e.g., 'shipping problems', 'billing inquiries')"
                },
                "date_range": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional date range as [start_date, end_date] in YYYY-MM-DD format (inclusive)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_suppliers",
        "description": "Search for supplier quality report records. Use this to find information about product defect rates, batch failures, supplier names, and quality issues.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about suppliers and quality (e.g., 'mechanical keyboard defects', 'high failure rate')"
                },
                "date_range": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional date range as [start_date, end_date] in YYYY-MM-DD format (inclusive)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_warehouse_logs",
        "description": "Search for warehouse log records. Use this to find information about warehouse operations, events (received, shipped, returned), order movements, and inventory.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about warehouse operations (e.g., 'items received', 'returned to warehouse')"
                },
                "date_range": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Optional date range as [start_date, end_date] in YYYY-MM-DD format (inclusive)"
                }
            },
            "required": ["query"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a retrieval tool and return formatted results.

    Args:
        tool_name: Name of the tool to execute (search_orders, search_refunds, etc)
        tool_input: Dict with 'query' and optional 'date_range' keys

    Returns:
        Formatted string with tool results, one record per line
    """
    query = tool_input.get("query", "")
    date_range = tool_input.get("date_range")

    # Map tool names to source_types
    source_type_map = {
        "search_orders": ["order"],
        "search_refunds": ["refund"],
        "search_tickets": ["support_ticket"],
        "search_suppliers": ["supplier_report"],
        "search_warehouse_logs": ["warehouse_log"],
    }

    source_types = source_type_map.get(tool_name, [])
    if not source_types:
        return f"Error: Unknown tool {tool_name}"

    # Convert date_range if provided
    date_range_tuple = None
    if date_range and len(date_range) == 2:
        date_range_tuple = (date_range[0], date_range[1])

    # Execute the search
    results = semantic_search(
        query=query,
        n_results=10,
        source_types=source_types,
        date_range=date_range_tuple
    )

    if not results:
        return f"No {source_types[0]} records found matching: {query}"

    # Format results: record_id | source_type | date | excerpt
    lines = []
    for result in results:
        record_id = result.get("record_id", "UNKNOWN")
        source_type = result.get("source_type", "unknown")
        date = result.get("metadata", {}).get("date", "N/A")
        distance = result.get("distance", 0)
        document = result.get("document", "")

        # Get a short excerpt (first 150 chars)
        excerpt = document[:150].replace("\n", " ")

        lines.append(f"{record_id} | {source_type} | {date} | {distance:.4f} | {excerpt}")

    return "\n".join(lines)
