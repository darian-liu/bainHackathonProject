from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Callable, Awaitable
from app.core.events import AgentEvent

EventCallback = Callable[[AgentEvent], Awaitable[None]]


class ChatAgent(ABC):
    @abstractmethod
    async def chat(
        self, 
        message: str, 
        context: List[str],
        on_event: EventCallback
    ) -> AsyncIterator[str]:
        """
        Stream chat response.
        
        Args:
            message: User's question
            context: Retrieved document chunks for RAG
            on_event: Callback to emit agent events
            
        Yields:
            Response text chunks
        """
        ...
