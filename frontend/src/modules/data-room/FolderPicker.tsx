import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Folder, FolderOpen, FileText, Loader2, Check, X, Upload } from 'lucide-react'
import { dataRoomApi } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { Folder as FolderType, File as FileType, IngestResult } from '@/types'

interface FolderPickerProps {
  selectedFolderId: string | null
  onSelectFolder: (folderId: string | null) => void
  onIngested: () => void
}

export function FolderPicker({
  selectedFolderId,
  onSelectFolder,
  onIngested,
}: FolderPickerProps) {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [ingestResults, setIngestResults] = useState<IngestResult[] | null>(null)

  // Fetch root folders
  const { data: folders, isLoading: loadingFolders } = useQuery({
    queryKey: ['folders'],
    queryFn: () => dataRoomApi.listFolders(),
  })

  // Fetch files for selected folder
  const { data: files, isLoading: loadingFiles } = useQuery({
    queryKey: ['files', selectedFolderId],
    queryFn: () => selectedFolderId ? dataRoomApi.listFiles(selectedFolderId) : Promise.resolve([]),
    enabled: !!selectedFolderId,
  })

  // Ingest mutation
  const ingestMutation = useMutation({
    mutationFn: dataRoomApi.ingestFolder,
    onSuccess: (results) => {
      setIngestResults(results)
    },
  })

  const toggleFolder = (folderId: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
    onSelectFolder(folderId)
  }

  const handleIngest = () => {
    if (selectedFolderId) {
      ingestMutation.mutate(selectedFolderId)
    }
  }

  const handleContinue = () => {
    onIngested()
  }

  const getStatusIcon = (status: string) => {
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

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Select a Folder to Ingest</CardTitle>
          <CardDescription>
            Choose a folder containing documents you want to chat with. Supported formats: PDF, DOCX, PPTX
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingFolders ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : folders && folders.length > 0 ? (
            <div className="space-y-4">
              {/* Folder list */}
              <div className="border rounded-lg divide-y">
                {folders.map((folder: FolderType) => (
                  <div key={folder.id}>
                    <button
                      onClick={() => toggleFolder(folder.id)}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left',
                        selectedFolderId === folder.id && 'bg-slate-100'
                      )}
                    >
                      {expandedFolders.has(folder.id) ? (
                        <FolderOpen className="w-5 h-5 text-amber-500" />
                      ) : (
                        <Folder className="w-5 h-5 text-amber-500" />
                      )}
                      <span className="font-medium">{folder.name}</span>
                    </button>
                    
                    {/* Files in folder */}
                    {expandedFolders.has(folder.id) && selectedFolderId === folder.id && (
                      <div className="bg-slate-50 px-4 py-2">
                        {loadingFiles ? (
                          <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Loading files...
                          </div>
                        ) : files && files.length > 0 ? (
                          <div className="space-y-1">
                            {files.map((file: FileType) => (
                              <div
                                key={file.id}
                                className="flex items-center gap-2 py-1 text-sm text-slate-600"
                              >
                                <FileText className="w-4 h-4 text-slate-400" />
                                <span>{file.name}</span>
                                <span className="text-xs text-muted-foreground ml-auto">
                                  {(file.size / 1024).toFixed(1)} KB
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground py-2">No files in this folder</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Ingest button */}
              {selectedFolderId && !ingestResults && (
                <Button
                  onClick={handleIngest}
                  disabled={ingestMutation.isPending}
                  className="w-full"
                >
                  {ingestMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Ingesting documents...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Ingest Selected Folder
                    </>
                  )}
                </Button>
              )}

              {/* Ingest results */}
              {ingestResults && (
                <div className="space-y-3">
                  <h4 className="font-medium">Ingestion Results</h4>
                  <div className="border rounded-lg divide-y">
                    {ingestResults.map((result, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-3 px-4 py-2"
                      >
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
                          <span className="text-xs text-red-500 ml-auto">
                            {result.error}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                  <Button onClick={handleContinue} className="w-full">
                    Start Chatting
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <Folder className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground">
                No folders found. Add documents to the demo-docs folder.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
