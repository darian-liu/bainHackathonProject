"""Tool-calling document agent using OpenAI function calling with AsyncOpenAI."""

import json
import os
import uuid
from pathlib import Path
from typing import Callable, Awaitable, Optional

from openai import AsyncOpenAI

from app.agents.prompts import DOCUMENT_AGENT_SYSTEM_PROMPT
from app.core.config import settings
from app.core.events import AgentEvent, EventType
from app.services.document_context import get_document_context
from app.db.database import get_database
from app.db.queries import experts as expert_queries

EventCallback = Callable[[AgentEvent], Awaitable[None]]

# Agent output directory (relative to backend root)
AGENT_OUTPUTS_DIR = Path(__file__).parent.parent.parent / "agent_outputs"

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search the document vector store for chunks relevant to a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant document chunks.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "List all unique documents available in the vector store.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_documents",
            "description": "Retrieve all chunks for a specific document by file_id for summarization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The file_id of the document to summarize.",
                    }
                },
                "required": ["file_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_document",
            "description": "Write content to a file in the agent_outputs directory for the user to download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename to write (e.g. 'summary.md').",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_experts",
            "description": "Query the expert database for a project. Returns expert profiles with screening scores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID to query experts for.",
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional status filter (e.g. 'recommended', 'scheduled', 'completed').",
                    },
                    "screening_grade": {
                        "type": "string",
                        "description": "Optional screening grade filter: 'strong', 'mixed', or 'weak'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of experts to return. Default 20.",
                    },
                },
                "required": ["project_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_expert_details",
            "description": "Get full details for a specific expert including sources and field provenance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expert_id": {
                        "type": "string",
                        "description": "The expert ID to get details for.",
                    }
                },
                "required": ["expert_id"],
            },
        },
    },
]


async def _execute_tool(
    name: str, arguments: dict, project_id: Optional[str]
) -> str:
    """Execute a tool call and return the result as a string."""
    ctx = get_document_context()

    if name == "search_documents":
        results = ctx.get_relevant_context(arguments["query"], n_results=5)
        if not results:
            return "No relevant documents found."
        parts = []
        for i, r in enumerate(results, 1):
            filename = r.get("metadata", {}).get("filename", "unknown")
            score = r.get("score", 0)
            parts.append(f"[{i}] {filename} (score: {score:.2f})\n{r['text'][:500]}")
        return "\n\n---\n\n".join(parts)

    elif name == "list_documents":
        docs = ctx.get_all_documents()
        if not docs:
            return "No documents have been ingested yet."
        lines = [f"- {d['filename']} (id: {d['file_id']})" for d in docs]
        return f"Available documents ({len(docs)}):\n" + "\n".join(lines)

    elif name == "summarize_documents":
        chunks = ctx.get_document_chunks(arguments["file_id"])
        if not chunks:
            return f"No chunks found for file_id '{arguments['file_id']}'."
        full_text = "\n\n".join(c["text"] for c in chunks)
        # Return the text for the LLM to summarize
        return f"Document content ({len(chunks)} chunks):\n\n{full_text[:8000]}"

    elif name == "write_document":
        filename = Path(arguments["filename"]).name  # prevent path traversal
        os.makedirs(AGENT_OUTPUTS_DIR, exist_ok=True)
        filepath = AGENT_OUTPUTS_DIR / filename
        filepath.write_text(arguments["content"], encoding="utf-8")
        return f"File written: {filename} ({len(arguments['content'])} chars). Available at /api/agent/download/{filename}"

    elif name == "query_experts":
        pid = arguments.get("project_id") or project_id
        if not pid:
            return "Error: No project_id provided. Please specify a project_id."

        db = await get_database()
        status_filter = arguments.get("status")
        all_experts = await expert_queries.list_experts(db, pid, status=status_filter)

        # Apply screening_grade filter if specified
        screening_grade = arguments.get("screening_grade")
        if screening_grade:
            all_experts = [
                e for e in all_experts
                if (e.get("screeningGrade") or "").lower() == screening_grade.lower()
            ]

        # Apply limit
        limit = arguments.get("limit", 20)
        experts = all_experts[:limit]

        if not experts:
            return "No experts found matching the filters."

        lines = []
        for e in experts:
            line = f"- **{e['canonicalName']}**"
            if e.get("canonicalEmployer"):
                line += f" | {e['canonicalEmployer']}"
            if e.get("canonicalTitle"):
                line += f" | {e['canonicalTitle']}"
            if e.get("screeningGrade"):
                line += f" | Grade: {e['screeningGrade']}"
            if e.get("screeningScore") is not None:
                line += f" (score: {e['screeningScore']})"
            if e.get("screeningRationale"):
                line += f"\n  Rationale: {e['screeningRationale'][:200]}"
            line += f"\n  Status: {e.get('status', 'unknown')} | ID: {e['id']}"
            lines.append(line)

        header = f"Found {len(all_experts)} experts"
        if len(experts) < len(all_experts):
            header += f" (showing {len(experts)})"
        return header + ":\n\n" + "\n\n".join(lines)

    elif name == "get_expert_details":
        db = await get_database()
        detail = await expert_queries.get_expert_with_full_details(
            db, arguments["expert_id"]
        )
        if not detail:
            return f"Expert '{arguments['expert_id']}' not found."

        parts = [
            f"# {detail['canonicalName']}",
            f"Employer: {detail.get('canonicalEmployer', 'N/A')}",
            f"Title: {detail.get('canonicalTitle', 'N/A')}",
            f"Status: {detail.get('status', 'N/A')}",
        ]
        if detail.get("screeningGrade"):
            parts.append(f"Screening: {detail['screeningGrade']} ({detail.get('screeningScore', 'N/A')})")
        if detail.get("screeningRationale"):
            parts.append(f"Rationale: {detail['screeningRationale']}")
        if detail.get("aiRecommendation"):
            parts.append(f"AI Recommendation: {detail['aiRecommendation']}")

        sources = detail.get("sources", [])
        if sources:
            parts.append(f"\n## Sources ({len(sources)})")
            for s in sources:
                network = s.get("email_network", "unknown")
                parts.append(f"- Network: {network}")
                for p in s.get("provenance", []):
                    parts.append(f"  - {p['fieldName']}: {p.get('extractedValue', 'N/A')}")

        return "\n".join(parts)

    return f"Unknown tool: {name}"


class DocumentAgent:
    """Tool-calling document agent using OpenAI function calling."""

    MAX_ITERATIONS = 10

    def __init__(self):
        client_config = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_config["base_url"] = settings.openai_base_url
        self.client = AsyncOpenAI(**client_config)
        self.model = settings.openai_model or "gpt-4o-mini"

    async def chat(
        self,
        message: str,
        conversation_history: list,
        on_event: EventCallback,
        project_id: Optional[str] = None,
    ) -> dict:
        """
        Run the agent loop.

        Returns dict with 'response' (final text) and 'tool_calls' (log of calls made).
        """
        agent_id = str(uuid.uuid4())

        await on_event(
            AgentEvent.create(
                EventType.AGENT_STARTED,
                agent_id,
                {"message": message, "project_id": project_id},
            )
        )

        # Build messages
        messages = [{"role": "system", "content": DOCUMENT_AGENT_SYSTEM_PROMPT}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": message})

        tool_calls_log = []

        try:
            for iteration in range(self.MAX_ITERATIONS):
                await on_event(
                    AgentEvent.create(
                        EventType.LLM_REQUEST,
                        agent_id,
                        {"model": self.model, "iteration": iteration},
                    )
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )

                choice = response.choices[0]

                await on_event(
                    AgentEvent.create(
                        EventType.LLM_RESPONSE,
                        agent_id,
                        {
                            "finish_reason": choice.finish_reason,
                            "iteration": iteration,
                            "has_tool_calls": bool(choice.message.tool_calls),
                        },
                    )
                )

                # Append assistant message to history
                messages.append(choice.message)

                # If the model wants to call tools, execute them
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        fn_name = tc.function.name
                        try:
                            fn_args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            fn_args = {}

                        await on_event(
                            AgentEvent.create(
                                EventType.TOOL_CALLED,
                                agent_id,
                                {"tool": fn_name, "arguments": fn_args},
                            )
                        )

                        result = await _execute_tool(fn_name, fn_args, project_id)

                        tool_calls_log.append({
                            "tool": fn_name,
                            "arguments": fn_args,
                            "result_preview": result[:200],
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })
                else:
                    # No tool calls — model produced its final response
                    final_text = choice.message.content or ""

                    await on_event(
                        AgentEvent.create(
                            EventType.AGENT_COMPLETED,
                            agent_id,
                            {"status": "success", "iterations": iteration + 1},
                        )
                    )

                    return {
                        "response": final_text,
                        "tool_calls": tool_calls_log,
                    }

            # Exhausted iterations — return whatever we have
            final_text = "I reached the maximum number of tool-calling steps. Here's what I found so far."
            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED,
                    agent_id,
                    {"status": "max_iterations", "iterations": self.MAX_ITERATIONS},
                )
            )
            return {"response": final_text, "tool_calls": tool_calls_log}

        except Exception as e:
            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED,
                    agent_id,
                    {"status": "error", "error": str(e)},
                )
            )
            raise
