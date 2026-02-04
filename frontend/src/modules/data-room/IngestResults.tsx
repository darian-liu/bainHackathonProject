import { Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { IngestResult } from '@/types'

interface IngestResultsProps {
  results: IngestResult[]
  onContinue: () => void
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'success':
      return <Check className="w-4 h-4 text-green-500" />
    case 'skipped':
      return <X className="w-4 h-4 text-yellow-500" />
    case 'error':
      return <X className="w-4 h-4 text-red-500" />
    default:
      return null
  }
}

export function IngestResults({ results, onContinue }: IngestResultsProps) {
  return (
    <div className="space-y-3">
      <h4 className="font-medium">Ingestion Results</h4>
      <div className="border rounded-lg divide-y">
        {results.map((result, index) => (
          <div key={index} className="flex items-center gap-3 px-4 py-2">
            {getStatusIcon(result.status)}
            <span className="text-sm">{result.file}</span>
            {result.chunks && (
              <span className="text-xs text-muted-foreground ml-auto">
                {result.chunks} chunks
              </span>
            )}
            {result.reason && (
              <span className="text-xs text-muted-foreground ml-auto">
                {result.reason}
              </span>
            )}
            {result.error && (
              <span className="text-xs text-red-500 ml-auto">{result.error}</span>
            )}
          </div>
        ))}
      </div>
      <Button onClick={onContinue} className="w-full">
        Start Chatting
      </Button>
    </div>
  )
}
