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
