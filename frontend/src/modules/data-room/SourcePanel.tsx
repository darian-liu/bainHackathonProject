import { FileText, X } from 'lucide-react'
import { useChatStore } from '@/stores/chatStore'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { SourceDocument } from '@/types'

interface SourcePanelProps {
  sources: SourceDocument[]
}

export function SourcePanel({ sources }: SourcePanelProps) {
  const setSelectedSources = useChatStore((s) => s.setSelectedSources)

  const handleClose = () => {
    setSelectedSources([])
  }

  // Group sources by filename
  const groupedSources = sources.reduce((acc, source) => {
    if (!acc[source.filename]) {
      acc[source.filename] = []
    }
    acc[source.filename].push(source)
    return acc
  }, {} as Record<string, SourceDocument[]>)

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="font-semibold">Sources</h3>
        <Button variant="ghost" size="icon" onClick={handleClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Sources list */}
      <ScrollArea className="flex-1 px-4">
        <div className="py-4 space-y-4">
          {Object.entries(groupedSources).map(([filename, fileSources]) => (
            <div key={filename} className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <FileText className="w-4 h-4 text-slate-400" />
                <span className="truncate">{filename}</span>
              </div>
              <div className="pl-6 space-y-1">
                {fileSources.map((source, index) => (
                  <div
                    key={`${source.file_id}-${source.chunk_index}`}
                    className="text-xs text-muted-foreground"
                  >
                    Chunk {source.chunk_index + 1}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
