from app.agents.base import ChatAgent, EventCallback
from app.core.events import AgentEvent, EventType
from typing import AsyncIterator, List
import uuid
import os


class CamelRAGAgent(ChatAgent):
    """RAG agent using CAMEL-AI framework."""
    
    def __init__(self):
        from camel.agents import ChatAgent as CamelChatAgent
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType, ModelType
        
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        system_msg = """You are a helpful assistant that answers questions based on provided context from documents.
        
Rules:
1. Only use information from the provided context
2. Always cite which document(s) you used
3. If the context doesn't contain the answer, say so clearly
4. Be concise but thorough"""
        
        self.agent = CamelChatAgent(
            system_message=system_msg,
            model=model
        )
    
    async def chat(
        self, 
        message: str, 
        context: List[str],
        on_event: EventCallback
    ) -> AsyncIterator[str]:
        agent_id = str(uuid.uuid4())
        
        # Emit start event
        await on_event(AgentEvent.create(
            EventType.AGENT_STARTED,
            agent_id,
            {"message": message, "context_chunks": len(context)}
        ))
        
        # Build RAG prompt
        context_str = "\n\n---\n\n".join(
            f"[Document {i+1}]\n{chunk}" 
            for i, chunk in enumerate(context)
        )
        
        prompt = f"""Based on the following document context, answer the user's question.

## Context
{context_str}

## Question
{message}

## Instructions
Provide a detailed answer and cite which document numbers you used (e.g., [Document 1])."""

        # Emit LLM request event
        await on_event(AgentEvent.create(
            EventType.LLM_REQUEST,
            agent_id,
            {"prompt_length": len(prompt), "model": "gpt-4o-mini"}
        ))
        
        try:
            # Get response from CAMEL agent
            response = self.agent.step(prompt)
            response_text = response.msg.content
            
            # Emit LLM response event
            await on_event(AgentEvent.create(
                EventType.LLM_RESPONSE,
                agent_id,
                {"response_length": len(response_text)}
            ))
            
            # Yield response (CAMEL doesn't stream by default, so yield all at once)
            yield response_text
            
            # Emit completion event
            await on_event(AgentEvent.create(
                EventType.AGENT_COMPLETED,
                agent_id,
                {"status": "success"}
            ))
            
        except Exception as e:
            await on_event(AgentEvent.create(
                EventType.AGENT_COMPLETED,
                agent_id,
                {"status": "error", "error": str(e)}
            ))
            raise
