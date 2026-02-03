from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    TOOL_CALLED = "tool_called"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    AGENT_COMPLETED = "agent_completed"


class AgentEvent(BaseModel):
    id: str
    type: EventType
    timestamp: datetime
    agent_id: str
    data: dict
    parent_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_type: EventType,
        agent_id: str,
        data: dict,
        parent_id: Optional[str] = None
    ) -> "AgentEvent":
        return cls(
            id=str(uuid.uuid4()),
            type=event_type,
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            data=data,
            parent_id=parent_id
        )
