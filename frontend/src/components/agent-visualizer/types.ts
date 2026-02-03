export type EventType = 
  | 'agent_started'
  | 'tool_called' 
  | 'llm_request'
  | 'llm_response'
  | 'agent_completed'

export interface AgentEvent {
  id: string
  type: EventType
  timestamp: string
  agent_id: string
  data: Record<string, unknown>
  parent_id?: string
}

export interface EventNodeData {
  event: AgentEvent
}
