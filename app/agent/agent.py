"""OpenRouter agent with simple prompt-based reasoning for multi-hop questions.

This agent uses OpenRouter with automatic model fallback to autonomously decide which retrieval tools to call
and chain evidence across multiple sources using prompt-based planning.
"""

import os
import re
import json
from dataclasses import dataclass
from typing import Optional, List
from openai import OpenAI
from app.agent.tools import execute_tool


@dataclass
class AgentResponse:
    """Response from the agent after answering a question."""
    final_answer: str
    tool_calls: List[dict]  # List of {tool_name, tool_input, result}
    cited_records: List[str]  # List of record_ids cited in the answer
    model_used: str = ""  # Track which model actually answered


class RetrievalAgent:
    """Single-agent tool-using reasoner with OpenRouter backend."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the agent with OpenRouter API key."""
        api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key or api_key == "your-openrouter-api-key-here":
            raise ValueError(
                "OPENROUTER_API_KEY not set or is placeholder. "
                "Set a valid OpenRouter API key in .env"
            )
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.models = [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat"
        ]
        self.model_used = ""

    def ask(self, question: str) -> AgentResponse:
        """Ask the agent a question and get back a reasoned answer with citations.

        The agent will:
        1. Decide which tool(s) to call based on the question
        2. Chain evidence across multiple tool calls for multi-hop questions
        3. Return a final answer with explicit citations to record_ids
        4. Explicitly note if evidence is insufficient

        Args:
            question: The question to ask

        Returns:
            AgentResponse with final_answer, tool_calls sequence, and cited_records
        """
        tool_calls = []

        # Phase 1: Planning - decide which tools to call
        plan_prompt = self._build_planning_prompt(question)
        plan_response = None
        last_error = None
        for model in self.models:
            try:
                plan_response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": plan_prompt}],
                    temperature=0,
                    max_tokens=1024
                )
                self.model_used = plan_response.model
                break
            except Exception as e:
                last_error = e
                if model == self.models[-1]:
                    raise last_error
                continue
        plan_text = plan_response.choices[0].message.content or ""

        # Phase 2: Execute tools based on plan
        tool_calls_text = self._extract_tool_calls(plan_text)

        for tool_spec in tool_calls_text:
            tool_name = tool_spec.get("tool")
            tool_input = tool_spec.get("input", {})

            result = execute_tool(tool_name, tool_input)
            tool_calls.append({
                "tool_name": tool_name,
                "tool_input": tool_input,
                "result": result
            })

        # Phase 3: Synthesis - synthesize final answer with all gathered evidence
        synthesis_prompt = self._build_synthesis_prompt(
            question, tool_calls
        )
        synthesis_response = None
        last_error = None
        for model in self.models:
            try:
                synthesis_response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": synthesis_prompt}],
                    temperature=0,
                    max_tokens=2048
                )
                self.model_used = synthesis_response.model
                break
            except Exception as e:
                last_error = e
                if model == self.models[-1]:
                    raise last_error
                continue
        final_answer = synthesis_response.choices[0].message.content or ""
        cited_records = self._extract_citations(final_answer)

        return AgentResponse(
            final_answer=final_answer,
            tool_calls=tool_calls,
            cited_records=cited_records,
            model_used=self.model_used
        )

    def _build_planning_prompt(self, question: str) -> str:
        """Build the planning prompt that asks which tools to call."""
        return f"""You are a data analyst helping answer questions about business operations.

You have access to 5 search tools:
1. search_orders - Find customer orders, items, totals, shipping
2. search_refunds - Find refunds, reasons, amounts, policy versions
3. search_tickets - Find support tickets, issues, categories, priorities
4. search_suppliers - Find supplier quality reports, defect rates, failures
5. search_warehouse_logs - Find warehouse operations, item movements, events

For multi-hop questions, plan a sequence of tool calls. Each tool accepts:
- query: natural language search string (required)
- date_range: optional [start_date, end_date] in YYYY-MM-DD format

Question: {question}

Respond with your plan. For each tool call you need, output it in this format:
TOOL_CALL: {{"tool": "tool_name", "input": {{"query": "search query", "date_range": ["2024-01-01", "2024-01-31"]}}}}

Make multiple TOOL_CALL lines if you need multiple searches. Keep it to 1-3 tool calls maximum."""

    def _extract_tool_calls(self, plan_text: str) -> List[dict]:
        """Extract tool calls from the planning response."""
        tool_calls = []
        lines = plan_text.split('\n')

        for line in lines:
            if 'TOOL_CALL:' in line:
                try:
                    json_str = line.split('TOOL_CALL:', 1)[1].strip()
                    tool_spec = json.loads(json_str)
                    tool_calls.append(tool_spec)
                except (json.JSONDecodeError, IndexError):
                    pass

        return tool_calls

    def _build_synthesis_prompt(self, question: str, tool_calls: List[dict]) -> str:
        """Build the synthesis prompt with gathered evidence."""
        evidence_text = ""
        for i, call in enumerate(tool_calls, 1):
            evidence_text += f"\n[Tool {i}] {call['tool_name']} with query: {call['tool_input'].get('query')}\n"
            evidence_text += "Results:\n"
            for line in call['result'].split('\n')[:15]:
                evidence_text += f"  {line}\n"
            if len(call['result'].split('\n')) > 15:
                evidence_text += f"  ... (truncated)\n"

        return f"""Based on the evidence gathered from searching our records, answer this question:

{question}

Evidence gathered:
{evidence_text}

Provide a final answer that:
1. Directly answers the question
2. Cites specific record_ids for every claim: (source: RECORD-ID) or (sources: RECORD-ID1, RECORD-ID2)
3. Only cite records that directly support your conclusion. Do NOT cite records you examined but found irrelevant or that showed no evidence.
4. Explicitly notes any unsupported claims: "No data found to verify this claim" or "This cannot be verified from available records"
5. Synthesizes findings across multiple searches if needed
6. Is clear and actionable for business decision-making

Keep your answer to 2-3 paragraphs maximum."""

    def _extract_citations(self, answer_text: str) -> List[str]:
        """Extract record_ids cited in (source: ...) or (sources: ...) markers.

        Only extracts record_ids that appear inside explicit (source: ...)
        or (sources: ...) markers. This ensures we only capture records
        explicitly cited as supporting evidence, not just mentioned anywhere
        in the text.

        Patterns matched:
        - (source: REF-001)
        - (sources: REF-001, REF-002)
        - (sources: REF-001, REF-002, REF-003)
        """
        # Match record_ids inside (source: ...) and (sources: ...) markers
        pattern = r'\(sources?:\s*([^)]+)\)'
        matches = []

        for match in re.finditer(pattern, answer_text):
            # Extract the content between "source:" and ")"
            content = match.group(1)
            # Find all record_ids in this content (separated by commas)
            record_ids = re.findall(r'\b([A-Z]{2,}-\d{3}(?:#\d)?)\b', content)
            matches.extend(record_ids)

        return sorted(set(matches))
