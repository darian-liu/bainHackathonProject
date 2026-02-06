import { useState, useCallback } from 'react'
import { Upload, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { uploadDocument, useAgentStore } from '@/stores/agentStore'

interface UploadStatus {
  filename: string
  status: 'uploading' | 'success' | 'error'
  chunks?: number
  error?: string
}

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploads, setUploads] = useState<UploadStatus[]>([])
  const addUploadedFile = useAgentStore((s) => s.addUploadedFile)

  const handleUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return

    for (const file of Array.from(files)) {
      // Add to uploads list
      setUploads((prev) => [
        ...prev,
        { filename: file.name, status: 'uploading' },
      ])

      try {
        const result = await uploadDocument(file)

        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? {
                ...u,
                status: result.success ? 'success' : 'error',
                chunks: result.chunks,
                error: result.error,
              }
              : u
          )
        )

        // Add to persistent file list and clear from upload status after a short delay
        if (result.success) {
          addUploadedFile({
            file_id: result.file_id || `upload-${file.name}`,
            filename: file.name,
            chunks: result.chunks || 0,
          })
          setTimeout(() => {
            setUploads((prev) => prev.filter((u) => u.filename !== file.name))
          }, 2000)
        }
      } catch (error) {
        setUploads((prev) =>
          prev.map((u) =>
            u.filename === file.name
              ? {
                ...u,
                status: 'error',
                error: error instanceof Error ? error.message : 'Upload failed',
              }
              : u
          )
        )
      }
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleUpload(e.dataTransfer.files)
    },
    [handleUpload]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleUpload(e.target.files)
      e.target.value = '' // Reset input
    },
    [handleUpload]
  )

  return (
    <div className="p-4">
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${isDragging
          ? 'border-primary bg-primary/5'
          : 'border-gray-200 hover:border-gray-300'
          }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
        <p className="text-sm text-gray-600">
          Drag & drop files here
        </p>
        <p className="text-xs text-gray-400 mt-1">
          or{' '}
          <label className="text-primary hover:underline cursor-pointer">
            browse
            <input
              type="file"
              className="hidden"
              multiple
              accept=".pdf,.docx,.pptx,.txt,.md"
              onChange={handleFileSelect}
            />
          </label>
        </p>
        <p className="text-xs text-gray-400 mt-2">
          PDF, DOCX, PPTX, TXT, MD
        </p>
      </div>

      {/* Upload status */}
      {uploads.length > 0 && (
        <div className="mt-3 space-y-2">
          {uploads.map((upload, i) => (
            <div
              key={`${upload.filename}-${i}`}
              className="flex items-center gap-2 text-sm"
            >
              {upload.status === 'uploading' && (
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              )}
              {upload.status === 'success' && (
                <CheckCircle className="w-4 h-4 text-green-500" />
              )}
              {upload.status === 'error' && (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              <span className="truncate flex-1">{upload.filename}</span>
              {upload.status === 'success' && upload.chunks && (
                <span className="text-xs text-gray-400">
                  {upload.chunks} chunks
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
