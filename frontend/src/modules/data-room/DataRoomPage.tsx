import { useState } from 'react'
import { FolderPicker } from './FolderPicker'
import { ChatInterface } from './ChatInterface'
import { SourcePanel } from './SourcePanel'
import { useChatStore } from '@/stores/chatStore'

export function DataRoomPage() {
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  const [isIngested, setIsIngested] = useState(false)
  const selectedSources = useChatStore((s) => s.selectedSources)

  return (
    <div className="h-full flex">
      {/* Left: Folder picker or Chat */}
      <div className="flex-1 flex flex-col">
        {!isIngested ? (
          <FolderPicker
            selectedFolderId={selectedFolderId}
            onSelectFolder={setSelectedFolderId}
            onIngested={() => setIsIngested(true)}
          />
        ) : (
          <ChatInterface />
        )}
      </div>

      {/* Right: Source panel */}
      {selectedSources.length > 0 && (
        <div className="w-80 border-l bg-white">
          <SourcePanel sources={selectedSources} />
        </div>
      )}
    </div>
  )
}
