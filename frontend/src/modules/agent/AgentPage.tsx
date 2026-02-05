import { useState, useEffect } from 'react'
import { AgentChat } from './AgentChat'
import { UploadZone } from './UploadZone'
import { ToolsPanel } from './ToolsPanel'
import { useAgentStore } from '@/stores/agentStore'

export function AgentPage() {
  const [showTools, setShowTools] = useState(false)
  const { loadTools, availableTools } = useAgentStore()

  useEffect(() => {
    loadTools()
  }, [loadTools])

  return (
    <div className="h-full flex">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        <AgentChat onToggleTools={() => setShowTools(!showTools)} />
      </div>

      {/* Right panel: Tools or Upload */}
      {showTools && (
        <div className="w-80 border-l bg-white flex flex-col">
          <div className="p-4 border-b">
            <h3 className="font-semibold">Available Tools</h3>
            <p className="text-xs text-gray-500 mt-1">
              The agent can use these tools automatically
            </p>
          </div>
          <div className="flex-1 overflow-auto">
            <ToolsPanel tools={availableTools} />
          </div>
          <div className="border-t">
            <UploadZone />
          </div>
        </div>
      )}
    </div>
  )
}
