import { useEffect } from 'react'
import { FileText, X } from 'lucide-react'
import { useAgentStore } from '@/stores/agentStore'
import { UploadZone } from './UploadZone'

export function ContextPanel() {
  const { uploadedFiles, loadUploadedFiles, removeUploadedFile } = useAgentStore()

  useEffect(() => {
    loadUploadedFiles()
  }, [loadUploadedFiles])

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Context Files</h3>
        <p className="text-xs text-gray-500 mt-1">
          Upload documents for the agent to reference
        </p>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-auto p-4 space-y-2">
        {uploadedFiles.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-8">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No files uploaded yet</p>
            <p className="text-xs mt-1">
              Upload documents below for the agent to reference
            </p>
          </div>
        ) : (
          uploadedFiles.map((file) => (
            <div
              key={file.file_id}
              className="flex items-center gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-100 group"
            >
              <FileText className="w-4 h-4 text-blue-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{file.filename}</p>
                <p className="text-xs text-gray-400">{file.chunks} chunks</p>
              </div>
              <button
                onClick={() => removeUploadedFile(file.file_id)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded transition-opacity"
                title="Remove from list"
              >
                <X className="w-3.5 h-3.5 text-gray-400" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Upload zone at bottom */}
      <div className="border-t">
        <UploadZone />
      </div>
    </div>
  )
}
