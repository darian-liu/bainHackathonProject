"""Document Agent - Tool-calling agent for document manipulation."""

import json
import uuid
import os
from typing import AsyncIterator, List, Optional, Any, Dict
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel, Field

from app.agents.base import ChatAgent, EventCallback
from app.core.events import AgentEvent, EventType
from app.core.config import settings
from app.services.document_context import get_document_context


# ============== Tool Definitions ============== #

class ToolDefinition(BaseModel):
    """Tool definition for the agent."""
    name: str
    description: str
    parameters: Dict[str, Any]


AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Read the full content of a specific document by its file ID. Returns all chunks concatenated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The unique file ID of the document to read"
                    }
                },
                "required": ["file_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search across all documents using semantic search. Returns the most relevant chunks matching the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant document sections"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5, max: 20)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            "description": "List all available documents in the data room with their metadata.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_documents",
            "description": "Generate a summary of one or more documents. Can summarize a single document or multiple documents together.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file IDs to summarize"
                    },
                    "focus": {
                        "type": "string",
                        "description": "Optional focus area for the summary (e.g., 'financial metrics', 'key risks')"
                    }
                },
                "required": ["file_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_document",
            "description": "Write content to a new document file. Use this to create reports, summaries, or analysis outputs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to create (e.g., 'summary.md', 'analysis.txt')"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["filename", "content"]
            }
        }
    }
]


# ============== Tool Implementations ============== #

class DocumentTools:
    """Tool implementations for document manipulation."""

    def __init__(self, output_dir: Optional[str] = None):
        self.doc_context = get_document_context()
        self.output_dir = Path(output_dir) if output_dir else Path("./agent_outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._openai_client = None

    @property
    def openai_client(self) -> OpenAI:
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            client_config = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                client_config["base_url"] = settings.openai_base_url
            self._openai_client = OpenAI(**client_config)
        return self._openai_client

    async def read_document(self, file_id: str) -> Dict[str, Any]:
        """Read full document content by file ID."""
        chunks = self.doc_context.get_document_chunks(file_id)

        if not chunks:
            return {
                "success": False,
                "error": f"Document with file_id '{file_id}' not found"
            }

        # Join all chunks into full content
        full_content = "\n\n".join(chunks)

        return {
            "success": True,
            "file_id": file_id,
            "content": full_content,
            "chunk_count": len(chunks)
        }

    async def search_documents(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Search documents semantically."""
        n_results = min(max(1, n_results), 20)  # Clamp between 1 and 20

        results = self.doc_context.search(query, n_results=n_results)

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "filename": r.filename,
                    "file_id": r.file_id,
                    "text": r.text,
                    "score": r.score,
                    "chunk_index": r.chunk_index
                }
                for r in results
            ],
            "result_count": len(results)
        }

    async def list_documents(self) -> Dict[str, Any]:
        """List all available documents."""
        documents = self.doc_context.get_all_documents()

        return {
            "success": True,
            "documents": [
                {
                    "file_id": d.file_id,
                    "filename": d.filename,
                    "chunk_count": d.chunk_count
                }
                for d in documents
            ],
            "total_count": len(documents)
        }

    async def summarize_documents(
        self,
        file_ids: List[str],
        focus: Optional[str] = None
    ) -> Dict[str, Any]:
        """Summarize one or more documents."""
        all_content = []

        for file_id in file_ids:
            chunks = self.doc_context.get_document_chunks(file_id)
            if chunks:
                # Get document info
                docs = self.doc_context.get_all_documents()
                filename = next(
                    (d.filename for d in docs if d.file_id == file_id),
                    file_id
                )
                content = "\n\n".join(chunks)
                all_content.append(f"=== {filename} ===\n{content}")

        if not all_content:
            return {
                "success": False,
                "error": "No documents found with the provided file IDs"
            }

        combined_content = "\n\n---\n\n".join(all_content)

        # Truncate if too long
        max_content_length = 30000
        if len(combined_content) > max_content_length:
            combined_content = combined_content[:max_content_length] + "\n\n[Content truncated...]"

        focus_instruction = f"\nFocus particularly on: {focus}" if focus else ""

        prompt = f"""Please provide a comprehensive summary of the following document(s).{focus_instruction}

{combined_content}

Provide:
1. Key points and main findings
2. Important details and data
3. Any notable conclusions or recommendations"""

        response = self.openai_client.chat.completions.create(
            model=settings.openai_model or "gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a document analyst. Provide clear, comprehensive summaries."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        summary = response.choices[0].message.content or ""

        return {
            "success": True,
            "summary": summary,
            "documents_summarized": len(file_ids),
            "focus": focus
        }

    async def write_document(self, filename: str, content: str) -> Dict[str, Any]:
        """Write content to a new file."""
        # Sanitize filename
        safe_filename = "".join(
            c for c in filename if c.isalnum() or c in "._-"
        )
        if not safe_filename:
            safe_filename = "output.txt"

        output_path = self.output_dir / safe_filename

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "filename": safe_filename,
                "path": str(output_path),
                "size_bytes": len(content.encode("utf-8"))
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to write file: {str(e)}"
            }

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        tool_map = {
            "read_document": self.read_document,
            "search_documents": self.search_documents,
            "list_documents": self.list_documents,
            "summarize_documents": self.summarize_documents,
            "write_document": self.write_document,
        }

        if tool_name not in tool_map:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        tool_func = tool_map[tool_name]

        try:
            return await tool_func(**arguments)
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============== Document Agent ============== #

DOCUMENT_AGENT_SYSTEM_PROMPT = """You are a helpful document analysis assistant with access to tools for reading, searching, and analyzing documents.

Your capabilities:
1. **list_documents** - See all available documents in the data room
2. **search_documents** - Find relevant information across all documents
3. **read_document** - Read the full content of a specific document
4. **summarize_documents** - Generate summaries of one or more documents
5. **write_document** - Create new documents with your analysis

When helping users:
- Start by understanding what documents are available if needed
- Use search to find relevant information efficiently
- Read full documents only when needed for comprehensive analysis
- Cite your sources when providing information
- Be thorough but concise in your responses

Always think step-by-step about which tools to use to best answer the user's question."""


class DocumentAgent(ChatAgent):
    """Tool-calling agent for document manipulation and analysis."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the document agent.

        Args:
            output_dir: Directory for writing output files
        """
        client_config = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_config["base_url"] = settings.openai_base_url

        self.client = OpenAI(**client_config)
        self.model = settings.openai_model or "gpt-4o"
        self.tools = DocumentTools(output_dir)
        self.conversation_history: List[Dict[str, Any]] = []

    async def chat(
        self,
        message: str,
        context: List[str],
        on_event: EventCallback
    ) -> AsyncIterator[str]:
        """
        Process a chat message with tool calling support.

        Args:
            message: User's message
            context: Document context chunks (may be empty for tool-based agent)
            on_event: Callback for emitting agent events

        Yields:
            Response text chunks
        """
        agent_id = str(uuid.uuid4())

        # Emit agent started
        await on_event(
            AgentEvent.create(
                EventType.AGENT_STARTED,
                agent_id,
                {"message": message, "has_context": bool(context)}
            )
        )

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        try:
            # Initial LLM call with tools
            await on_event(
                AgentEvent.create(
                    EventType.LLM_REQUEST,
                    agent_id,
                    {"model": self.model, "has_tools": True}
                )
            )

            messages = [
                {"role": "system", "content": DOCUMENT_AGENT_SYSTEM_PROMPT},
                *self.conversation_history
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.3
            )

            assistant_message = response.choices[0].message

            # Process tool calls in a loop
            max_iterations = 10
            iteration = 0

            while assistant_message.tool_calls and iteration < max_iterations:
                iteration += 1

                # Add assistant message with tool calls to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    # Emit tool called event
                    await on_event(
                        AgentEvent.create(
                            EventType.TOOL_CALLED,
                            agent_id,
                            {
                                "tool": tool_name,
                                "arguments": arguments,
                                "tool_call_id": tool_call.id
                            }
                        )
                    )

                    # Execute the tool
                    result = await self.tools.execute_tool(tool_name, arguments)

                    # Emit tool completed event
                    await on_event(
                        AgentEvent.create(
                            EventType.TOOL_COMPLETED,
                            agent_id,
                            {
                                "tool": tool_name,
                                "success": result.get("success", False),
                                "tool_call_id": tool_call.id
                            }
                        )
                    )

                    # Add tool result to history
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Make another LLM call with tool results
                await on_event(
                    AgentEvent.create(
                        EventType.LLM_REQUEST,
                        agent_id,
                        {"model": self.model, "iteration": iteration}
                    )
                )

                messages = [
                    {"role": "system", "content": DOCUMENT_AGENT_SYSTEM_PROMPT},
                    *self.conversation_history
                ]

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=AGENT_TOOLS,
                    tool_choice="auto",
                    temperature=0.3
                )

                assistant_message = response.choices[0].message

            # Final response
            final_content = assistant_message.content or ""

            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": final_content
            })

            await on_event(
                AgentEvent.create(
                    EventType.LLM_RESPONSE,
                    agent_id,
                    {"response_length": len(final_content)}
                )
            )

            # Yield the response
            yield final_content

            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED,
                    agent_id,
                    {"status": "success", "tool_calls_made": iteration}
                )
            )

        except Exception as e:
            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED,
                    agent_id,
                    {"status": "error", "error": str(e)}
                )
            )
            raise

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools with their descriptions."""
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "parameters": tool["function"]["parameters"]
            }
            for tool in AGENT_TOOLS
        ]
