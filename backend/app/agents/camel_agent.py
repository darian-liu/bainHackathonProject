from app.agents.base import ChatAgent, EventCallback
from app.agents.prompts import build_context_string, build_rag_prompt, RAG_SYSTEM_PROMPT
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
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        self.agent = CamelChatAgent(system_message=RAG_SYSTEM_PROMPT, model=model)

    async def chat(
        self, message: str, context: List[str], on_event: EventCallback
    ) -> AsyncIterator[str]:
        agent_id = str(uuid.uuid4())

        # Emit start event
        await on_event(
            AgentEvent.create(
                EventType.AGENT_STARTED,
                agent_id,
                {"message": message, "context_chunks": len(context)},
            )
        )

        # Build RAG prompt using shared functions
        context_str = build_context_string(context)
        prompt = build_rag_prompt(context_str, message)

        # Emit LLM request event
        await on_event(
            AgentEvent.create(
                EventType.LLM_REQUEST,
                agent_id,
                {"prompt_length": len(prompt), "model": "gpt-4o-mini"},
            )
        )

        try:
            # Get response from CAMEL agent
            response = self.agent.step(prompt)
            response_text = response.msg.content

            # Emit LLM response event
            await on_event(
                AgentEvent.create(
                    EventType.LLM_RESPONSE,
                    agent_id,
                    {"response_length": len(response_text)},
                )
            )

            # Yield response (CAMEL doesn't stream by default, so yield all at once)
            yield response_text

            # Emit completion event
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
