from openai import OpenAI
from app.agents.base import ChatAgent, EventCallback
from app.core.events import AgentEvent, EventType
from typing import AsyncIterator, List
import uuid
import os


class SimpleChatAgent(ChatAgent):
    """Fallback agent using direct OpenAI API calls."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
    
    async def chat(
        self, 
        message: str, 
        context: List[str],
        on_event: EventCallback
    ) -> AsyncIterator[str]:
        agent_id = str(uuid.uuid4())
        
        await on_event(AgentEvent.create(
            EventType.AGENT_STARTED,
            agent_id,
            {"message": message, "context_chunks": len(context)}
        ))
        
        context_str = "\n\n---\n\n".join(
            f"[Document {i+1}]\n{chunk}" 
            for i, chunk in enumerate(context)
        )
        
        system_prompt = """You are a helpful assistant that answers questions based on provided document context.
Always cite which document numbers you used. If the context doesn't contain the answer, say so."""

        user_prompt = f"""Context:
{context_str}

Question: {message}"""

        await on_event(AgentEvent.create(
            EventType.LLM_REQUEST,
            agent_id,
            {"model": self.model}
        ))
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=True
            )
            
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
            await on_event(AgentEvent.create(
                EventType.LLM_RESPONSE,
                agent_id,
                {"response_length": len(full_response)}
            ))
            
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
