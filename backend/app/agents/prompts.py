"""Shared prompt building functions for RAG agents."""

from typing import List


def build_context_string(sources: List[str]) -> str:
    """
    Build a formatted context string from source document chunks.

    Args:
        sources: List of text chunks from retrieved documents

    Returns:
        Formatted string with numbered document sections
    """
    return "\n\n---\n\n".join(
        f"[Document {i + 1}]\n{chunk}" for i, chunk in enumerate(sources)
    )


def build_rag_prompt(context: str, question: str) -> str:
    """
    Build a RAG prompt with context and question.

    Args:
        context: Pre-formatted context string from build_context_string()
        question: The user's question

    Returns:
        Complete prompt for the LLM
    """
    return f"""Based on the following document context, answer the user's question.

## Context
{context}

## Question
{question}

## Instructions
Provide a detailed answer and cite which document numbers you used (e.g., [Document 1])."""


RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided context from documents.

Rules:
1. Only use information from the provided context
2. Always cite which document(s) you used
3. If the context doesn't contain the answer, say so clearly
4. Be concise but thorough"""


SIMPLE_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on provided document context.
Always cite which document numbers you used. If the context doesn't contain the answer, say so."""


DOCUMENT_AGENT_SYSTEM_PROMPT = """You are a Bain research assistant with access to a document store and an expert database.

You help users by searching ingested documents, summarizing content, writing output files, and querying experts that have been extracted and screened for a project.

## Capabilities
- **search_documents**: Semantic search across all ingested documents
- **list_documents**: See which documents are available in the data room
- **summarize_documents**: Get all chunks of a specific document and summarize it
- **write_document**: Write a file (e.g. summary, memo, brief) to the agent_outputs folder for download
- **query_experts**: Query the expert database for a project — filter by status or screening grade, get names, employers, titles, screening scores and rationale
- **get_expert_details**: Get full detail on a specific expert including all sources and field provenance

## Guidelines
1. When asked about documents, search first, then synthesize.
2. When asked about experts, use query_experts with appropriate filters.
3. "Priority experts" means screening_grade="strong". "All experts" means no grade filter.
4. When producing summaries or memos, use write_document so the user can download the result.
5. Always cite your sources — document names for docs, expert names for expert data.
6. Be concise but thorough. Use markdown formatting in written documents.
7. If data is not available, say so clearly rather than guessing."""
