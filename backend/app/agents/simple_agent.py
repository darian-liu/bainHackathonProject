from openai import OpenAI
from app.agents.base import ChatAgent, EventCallback
from app.agents.prompts import build_context_string, SIMPLE_SYSTEM_PROMPT
from app.core.events import AgentEvent, EventType
from app.core.config import settings
from typing import AsyncIterator, List
import uuid


class SimpleChatAgent(ChatAgent):
    """Fallback agent using direct OpenAI API calls."""

    def __init__(self):
        # Configure client with optional Portkey base URL
        client_config = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_config["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_config)
        
        # Use model from settings (Bain uses @personal-openai/ prefix with Portkey)
        self.model = settings.openai_model or "gpt-4o-mini"

    async def chat(
        self, message: str, context: List[str], on_event: EventCallback
    ) -> AsyncIterator[str]:
        agent_id = str(uuid.uuid4())

        await on_event(
            AgentEvent.create(
                EventType.AGENT_STARTED,
                agent_id,
                {"message": message, "context_chunks": len(context)},
            )
        )

        # Build context using shared function
        context_str = build_context_string(context)

        user_prompt = f"""Context:
{context_str}

Question: {message}"""

        await on_event(
            AgentEvent.create(EventType.LLM_REQUEST, agent_id, {"model": self.model})
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SIMPLE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
            )

            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            await on_event(
                AgentEvent.create(
                    EventType.LLM_RESPONSE,
                    agent_id,
                    {"response_length": len(full_response)},
                )
            )

            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED, agent_id, {"status": "success"}
                )
            )

        except Exception as e:
            await on_event(
                AgentEvent.create(
                    EventType.AGENT_COMPLETED,
                    agent_id,
                    {"status": "error", "error": str(e)},
                )
            )
            raise
