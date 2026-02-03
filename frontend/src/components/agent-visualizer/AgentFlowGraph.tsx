import { useMemo } from 'react'
import ReactFlow, { 
  Node, 
  Edge, 
  Background, 
  Controls,
  ConnectionMode,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useAgentEventStore } from '@/stores/agentEventStore'
import { EventNode } from './EventNode'
import type { AgentEvent } from './types'

const nodeTypes = { eventNode: EventNode }

function buildGraph(events: AgentEvent[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = events.map((event, index) => ({
    id: event.id,
    type: 'eventNode',
    position: { x: 150, y: index * 100 + 50 },
    data: { event },
  }))
  
  const edges: Edge[] = []
  
  // Group events by agent_id
  const agentEvents = events.reduce((acc, e) => {
    if (!acc[e.agent_id]) acc[e.agent_id] = []
    acc[e.agent_id].push(e)
    return acc
  }, {} as Record<string, AgentEvent[]>)
  
  // Create edges between sequential events within same agent
  Object.values(agentEvents).forEach((agentEvts) => {
    for (let i = 1; i < agentEvts.length; i++) {
      edges.push({
        id: `edge-${agentEvts[i - 1].id}-${agentEvts[i].id}`,
        source: agentEvts[i - 1].id,
        target: agentEvts[i].id,
        animated: true,
        style: { stroke: '#6366f1' },
      })
    }
  })
  
  return { nodes, edges }
}

export function AgentFlowGraph() {
  const events = useAgentEventStore((s) => s.events)
  const { nodes, edges } = useMemo(() => buildGraph(events), [events])

  return (
    <div className="h-full w-full bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
      >
        <Background color="#94a3b8" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  )
}
