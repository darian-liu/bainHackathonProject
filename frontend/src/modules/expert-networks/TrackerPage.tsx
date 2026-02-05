/**
 * Tracker Page - Main expert tracker table
 * Simplified MVP version focused on core functionality
 */

import { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Loader2, Search, RefreshCw, ArrowLeft, Undo2, Redo2, AlertCircle, CheckCircle2, X, Settings2, Plus, Trash2, Sparkles, ArrowUpDown, ArrowUp, ArrowDown, Filter, Eye } from 'lucide-react'
import { useExperts, useUpdateExpert, useProject, useLatestIngestionLog, useUndoIngestion, useRedoIngestion, useUpdateScreenerConfig, useScreenExpert, useScreenAllExperts, expertNetworksApi } from './api'
import { ExpertDetailPanel } from './ExpertDetailPanel'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import type { Expert, ExpertStatus, ScreenerQuestion } from './types'

export function TrackerPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { data: projectData } = useProject(projectId!)
  const { data, isLoading, refetch } = useExperts(projectId!)
  const { data: ingestionLogData, refetch: refetchLog } = useLatestIngestionLog(projectId!)
  const undoIngestion = useUndoIngestion()
  const redoIngestion = useRedoIngestion()
  const updateExpert = useUpdateExpert()

  const updateScreenerConfig = useUpdateScreenerConfig()
  const screenAllExperts = useScreenAllExperts()
  
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [isExporting, setIsExporting] = useState(false)
  const [showChangeSummary, setShowChangeSummary] = useState(true)
  const [showScreenerConfig, setShowScreenerConfig] = useState(false)
  const [screenerQuestions, setScreenerQuestions] = useState<ScreenerQuestion[]>(
    projectData?.screenerConfig?.questions || []
  )
  const [autoScreenEnabled, setAutoScreenEnabled] = useState(
    projectData?.screenerConfig?.autoScreen || false
  )
  const [screeningProgress, setScreeningProgress] = useState<{
    isScreening: boolean
    screened: number
    total: number
  } | null>(null)
  
  // Expert detail panel state
  const [selectedExpertId, setSelectedExpertId] = useState<string | null>(null)
  
  // Sorting state
  const [sortConfig, setSortConfig] = useState<{
    column: string | null
    direction: 'asc' | 'desc'
  }>({ column: null, direction: 'asc' })
  
  // Column filters state
  const [columnFilters, setColumnFilters] = useState<{
    screening: string[]
    conflict: string[]
    status: string[]
    name: string
    employer: string
    title: string
    lead: string
    interviewDateFrom: string
    interviewDateTo: string
  }>({
    screening: [],
    conflict: [],
    status: [],
    name: '',
    employer: '',
    title: '',
    lead: '',
    interviewDateFrom: '',
    interviewDateTo: '',
  })
  
  // Column widths state with localStorage persistence
  const LOCAL_STORAGE_KEY = `tracker-column-widths-${projectId}`
  const defaultColumnWidths = {
    details: 48,
    name: 192,
    employer: 160,
    title: 160,
    status: 144,
    conflict: 128,
    interviewDate: 144,
    lead: 128,
    screening: 144,
  }
  
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          return defaultColumnWidths
        }
      }
    }
    return defaultColumnWidths
  })
  
  // Persist column widths to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(columnWidths))
    }
  }, [columnWidths, LOCAL_STORAGE_KEY])
  
  // Resizing state
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const resizeStartX = useRef<number>(0)
  const resizeStartWidth = useRef<number>(0)
  
  const handleResizeStart = useCallback((e: React.MouseEvent, column: string) => {
    e.preventDefault()
    setResizingColumn(column)
    resizeStartX.current = e.clientX
    resizeStartWidth.current = columnWidths[column] || defaultColumnWidths[column as keyof typeof defaultColumnWidths] || 100
  }, [columnWidths, defaultColumnWidths])
  
  useEffect(() => {
    if (!resizingColumn) return
    
    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX.current
      const newWidth = Math.max(50, resizeStartWidth.current + diff) // Min width 50px
      setColumnWidths(prev => ({ ...prev, [resizingColumn]: newWidth }))
    }
    
    const handleMouseUp = () => {
      setResizingColumn(null)
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [resizingColumn])

  const experts = data?.experts || []
  
  // Selected expert for detail panel (must be after experts declaration)
  const selectedExpert = experts.find(e => e.id === selectedExpertId) || null

  // Filter, search, and sort experts
  const filteredExperts = useMemo(() => {
    let result = experts

    // Status filter (column-level, replacing global)
    if (columnFilters.status.length > 0) {
      result = result.filter((e) => columnFilters.status.includes(e.status))
    }
    // Fallback for global status filter
    if (statusFilter !== 'all') {
      result = result.filter((e) => e.status === statusFilter)
    }

    // Search
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (e) =>
          e.canonicalName.toLowerCase().includes(query) ||
          e.canonicalEmployer?.toLowerCase().includes(query) ||
          e.canonicalTitle?.toLowerCase().includes(query)
      )
    }
    
    // Text filters
    if (columnFilters.name) {
      const query = columnFilters.name.toLowerCase()
      result = result.filter((e) => e.canonicalName.toLowerCase().includes(query))
    }
    if (columnFilters.employer) {
      const query = columnFilters.employer.toLowerCase()
      result = result.filter((e) => (e.canonicalEmployer || '').toLowerCase().includes(query))
    }
    if (columnFilters.title) {
      const query = columnFilters.title.toLowerCase()
      result = result.filter((e) => (e.canonicalTitle || '').toLowerCase().includes(query))
    }
    if (columnFilters.lead) {
      const query = columnFilters.lead.toLowerCase()
      result = result.filter((e) => (e.assignedLead || '').toLowerCase().includes(query))
    }
    
    // Date range filters - Interview Date
    if (columnFilters.interviewDateFrom) {
      result = result.filter((e) => {
        if (!e.interviewDate) return false
        return e.interviewDate >= columnFilters.interviewDateFrom
      })
    }
    if (columnFilters.interviewDateTo) {
      result = result.filter((e) => {
        if (!e.interviewDate) return false
        return e.interviewDate <= columnFilters.interviewDateTo
      })
    }
    
    // Column filters - Screening
    if (columnFilters.screening.length > 0) {
      result = result.filter((e) => {
        if (columnFilters.screening.includes('none') && !e.aiScreeningGrade) return true
        if (e.aiScreeningGrade && columnFilters.screening.includes(e.aiScreeningGrade)) return true
        return false
      })
    }
    
    // Column filters - Conflict
    if (columnFilters.conflict.length > 0) {
      result = result.filter((e) => {
        if (columnFilters.conflict.includes('none') && !e.conflictStatus) return true
        if (e.conflictStatus && columnFilters.conflict.includes(e.conflictStatus)) return true
        return false
      })
    }
    
    // Sorting
    if (sortConfig.column) {
      result = [...result].sort((a, b) => {
        let aVal: any
        let bVal: any
        
        switch (sortConfig.column) {
          case 'name':
            aVal = a.canonicalName.toLowerCase()
            bVal = b.canonicalName.toLowerCase()
            break
          case 'employer':
            aVal = (a.canonicalEmployer || '').toLowerCase()
            bVal = (b.canonicalEmployer || '').toLowerCase()
            break
          case 'title':
            aVal = (a.canonicalTitle || '').toLowerCase()
            bVal = (b.canonicalTitle || '').toLowerCase()
            break
          case 'status':
            aVal = a.status
            bVal = b.status
            break
          case 'conflict':
            aVal = a.conflictStatus || 'zzz' // Put nulls at end
            bVal = b.conflictStatus || 'zzz'
            break
          case 'screening':
            // Sort by score (nulls at end)
            aVal = a.aiScreeningScore ?? -1
            bVal = b.aiScreeningScore ?? -1
            break
          case 'interviewDate':
            aVal = a.interviewDate || ''
            bVal = b.interviewDate || ''
            break
          case 'lead':
            aVal = (a.assignedLead || '').toLowerCase()
            bVal = (b.assignedLead || '').toLowerCase()
            break
          default:
            return 0
        }
        
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
        return 0
      })
    }

    return result
  }, [experts, statusFilter, searchQuery, sortConfig, columnFilters])

  const handleUpdate = async (expertId: string, field: keyof Expert, value: any) => {
    try {
      await updateExpert.mutateAsync({
        expertId,
        updates: { [field]: value },
      })
    } catch (error) {
      console.error('Update failed:', error)
    }
  }

  const handleExport = async () => {
    if (!projectId) return
    setIsExporting(true)
    try {
      const blob = await expertNetworksApi.exportCSV(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `experts_${projectData?.name || projectId}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setIsExporting(false)
    }
  }

  const handleScreenAll = async () => {
    if (!projectId) return
    const unscreenedCount = experts.filter(e => !e.aiScreeningGrade).length
    if (unscreenedCount === 0) {
      alert('All experts have already been screened!')
      return
    }
    
    setScreeningProgress({ isScreening: true, screened: 0, total: unscreenedCount })
    
    try {
      const result = await screenAllExperts.mutateAsync({ projectId })
      setScreeningProgress({ isScreening: false, screened: result.screened, total: unscreenedCount })
      refetch()
      
      // Clear progress after 3 seconds
      setTimeout(() => setScreeningProgress(null), 3000)
    } catch (error) {
      console.error('Screen all failed:', error)
      setScreeningProgress(null)
    }
  }

  const unscreenedCount = useMemo(() => 
    experts.filter(e => !e.aiScreeningGrade).length, 
    [experts]
  )
  
  // Toggle sort for a column
  const toggleSort = (column: string) => {
    setSortConfig(prev => {
      if (prev.column === column) {
        // Cycle: asc -> desc -> none
        if (prev.direction === 'asc') {
          return { column, direction: 'desc' }
        } else {
          return { column: null, direction: 'asc' }
        }
      }
      return { column, direction: 'asc' }
    })
  }
  
  // Toggle a multi-select filter value
  const toggleFilter = (filterType: 'screening' | 'conflict' | 'status', value: string) => {
    setColumnFilters(prev => {
      const current = prev[filterType] as string[]
      const newValues = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value]
      return { ...prev, [filterType]: newValues }
    })
  }
  
  // Set a text filter value
  const setTextFilter = (filterType: 'name' | 'employer' | 'title' | 'lead', value: string) => {
    setColumnFilters(prev => ({ ...prev, [filterType]: value }))
  }
  
  // Set a date filter value
  const setDateFilter = (filterType: 'interviewDateFrom' | 'interviewDateTo', value: string) => {
    setColumnFilters(prev => ({ ...prev, [filterType]: value }))
  }
  
  // Clear all filters
  const clearFilters = () => {
    setColumnFilters({ 
      screening: [], 
      conflict: [], 
      status: [],
      name: '',
      employer: '',
      title: '',
      lead: '',
      interviewDateFrom: '',
      interviewDateTo: '',
    })
    setStatusFilter('all')
    setSearchQuery('')
  }
  
  const hasActiveFilters = columnFilters.screening.length > 0 || 
    columnFilters.conflict.length > 0 || 
    columnFilters.status.length > 0 ||
    columnFilters.name || 
    columnFilters.employer || 
    columnFilters.title || 
    columnFilters.lead ||
    columnFilters.interviewDateFrom ||
    columnFilters.interviewDateTo ||
    statusFilter !== 'all' || 
    searchQuery

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/expert-networks')}
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{projectData?.name || 'Expert Tracker'}</h1>
            <p className="text-gray-600">{filteredExperts.length} experts</p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => {
              setScreenerQuestions(projectData?.screenerConfig?.questions || [])
              setAutoScreenEnabled(projectData?.screenerConfig?.autoScreen || false)
              setShowScreenerConfig(true)
            }}
          >
            <Settings2 className="w-4 h-4 mr-1" />
            Screener Config
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleScreenAll}
            disabled={screenAllExperts.isPending || unscreenedCount === 0}
            title={unscreenedCount === 0 ? 'All experts screened' : `Screen ${unscreenedCount} unscreened experts`}
          >
            {screenAllExperts.isPending ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 mr-1" />
            )}
            Screen All {unscreenedCount > 0 && `(${unscreenedCount})`}
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-1" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-1" />
            )}
            Export CSV
          </Button>
          <Button size="sm" onClick={() => navigate(`/expert-networks/${projectId}/ingest`)}>
            Ingest Email
          </Button>
        </div>
      </div>

      {/* Screener Config Dialog */}
      <ScreenerConfigDialog
        open={showScreenerConfig}
        onOpenChange={setShowScreenerConfig}
        questions={screenerQuestions}
        onQuestionsChange={setScreenerQuestions}
        autoScreen={autoScreenEnabled}
        onAutoScreenChange={setAutoScreenEnabled}
        onSave={async () => {
          await updateScreenerConfig.mutateAsync({
            projectId: projectId!,
            screenerConfig: { questions: screenerQuestions, autoScreen: autoScreenEnabled },
          })
          setShowScreenerConfig(false)
        }}
        isSaving={updateScreenerConfig.isPending}
      />

      {/* Screening Progress Banner */}
      {screeningProgress && (
        <div className={`border rounded-lg p-4 ${screeningProgress.isScreening ? 'bg-purple-50 border-purple-200' : 'bg-green-50 border-green-200'}`}>
          <div className="flex items-center gap-3">
            {screeningProgress.isScreening ? (
              <>
                <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                <div>
                  <p className="font-medium text-purple-900">Screening experts with AI...</p>
                  <p className="text-sm text-purple-700">This may take a moment</p>
                </div>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-5 h-5 text-green-600" />
                <div>
                  <p className="font-medium text-green-900">Screening Complete</p>
                  <p className="text-sm text-green-700">
                    Screened {screeningProgress.screened} of {screeningProgress.total} experts
                  </p>
                </div>
                <button
                  onClick={() => setScreeningProgress(null)}
                  className="ml-auto text-green-400 hover:text-green-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Change Summary Banner */}
      {showChangeSummary && ingestionLogData?.log && ingestionLogData.log.status === 'completed' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1">
              <CheckCircle2 className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-blue-900">Last Ingestion Summary</p>
                <div className="text-sm text-blue-700 mt-1 space-x-4">
                  {ingestionLogData.log.summary.addedCount > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">{ingestionLogData.log.summary.addedCount}</span> added
                    </span>
                  )}
                  {ingestionLogData.log.summary.updatedCount > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">{ingestionLogData.log.summary.updatedCount}</span> updated
                    </span>
                  )}
                  {ingestionLogData.log.summary.mergedCount > 0 && (
                    <span className="inline-flex items-center gap-1">
                      <span className="font-medium">{ingestionLogData.log.summary.mergedCount}</span> merged
                    </span>
                  )}
                  {ingestionLogData.log.summary.needsReviewCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-amber-600">
                      <AlertCircle className="w-4 h-4" />
                      <span className="font-medium">{ingestionLogData.log.summary.needsReviewCount}</span> need review
                    </span>
                  )}
                </div>
                
                {/* Detailed changes list */}
                {ingestionLogData.log.entries && ingestionLogData.log.entries.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-blue-200">
                    <ul className="text-xs space-y-1.5 text-blue-800">
                      {ingestionLogData.log.entries.slice(0, 10).map((entry) => (
                        <li key={entry.id} className="flex items-start gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${
                            entry.action === 'added' ? 'bg-green-100 text-green-700' :
                            entry.action === 'updated' ? 'bg-blue-100 text-blue-700' :
                            entry.action === 'merged' ? 'bg-purple-100 text-purple-700' :
                            'bg-amber-100 text-amber-700'
                          }`}>
                            {entry.action}
                          </span>
                          <span className="font-medium">{entry.expertName || 'Unknown'}</span>
                          {entry.fieldsChanged && entry.fieldsChanged.length > 0 && (
                            <span className="text-blue-600">
                              ({entry.fieldsChanged.join(', ')})
                            </span>
                          )}
                        </li>
                      ))}
                      {ingestionLogData.log.entries.length > 10 && (
                        <li className="text-blue-500 italic">
                          ...and {ingestionLogData.log.entries.length - 10} more
                        </li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  if (ingestionLogData.log) {
                    await undoIngestion.mutateAsync({
                      projectId: projectId!,
                      logId: ingestionLogData.log.id,
                    })
                    refetch()
                    refetchLog()
                  }
                }}
                disabled={undoIngestion.isPending}
              >
                {undoIngestion.isPending ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Undo2 className="w-4 h-4 mr-1" />
                )}
                Undo
              </Button>
              <button
                onClick={() => setShowChangeSummary(false)}
                className="text-blue-400 hover:text-blue-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Undone Ingestion Banner (with Redo) */}
      {showChangeSummary && ingestionLogData?.log && ingestionLogData.log.status === 'undone' && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1">
              <Undo2 className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-medium text-amber-900">Last Ingestion Undone</p>
                <p className="text-sm text-amber-700 mt-1">
                  The previous ingestion was reverted. Click Redo to restore the changes.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  if (ingestionLogData.log) {
                    await redoIngestion.mutateAsync({
                      projectId: projectId!,
                      logId: ingestionLogData.log.id,
                    })
                    refetch()
                    refetchLog()
                  }
                }}
                disabled={redoIngestion.isPending}
              >
                {redoIngestion.isPending ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <Redo2 className="w-4 h-4 mr-1" />
                )}
                Redo
              </Button>
              <button
                onClick={() => setShowChangeSummary(false)}
                className="text-amber-400 hover:text-amber-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-center">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search by name, employer, or title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="recommended">Recommended</SelectItem>
            <SelectItem value="awaiting_screeners">Awaiting Screeners</SelectItem>
            <SelectItem value="shortlisted">Shortlisted</SelectItem>
            <SelectItem value="requested">Requested</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="declined">Declined</SelectItem>
            <SelectItem value="conflict">Conflict</SelectItem>
          </SelectContent>
        </Select>
        
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="text-gray-500">
            <X className="w-4 h-4 mr-1" />
            Clear filters
          </Button>
        )}
      </div>

      {/* Table */}
      {filteredExperts.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          {experts.length === 0 ? (
            <>
              <p className="mb-4">No experts yet</p>
              <Button onClick={() => navigate(`/expert-networks/${projectId}/ingest`)}>
                Ingest Your First Email
              </Button>
            </>
          ) : (
            <p>No experts match your filters</p>
          )}
        </div>
      ) : (
        <div className="border rounded-lg overflow-x-auto">
          <Table className="min-w-[1200px]" style={{ tableLayout: 'fixed' }}>
            <TableHeader>
              <TableRow>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.details }}
                >
                  <span className="text-xs text-gray-500">Details</span>
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'details')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.name }}
                >
                  <TextFilterHeader 
                    column="name" 
                    label="Name" 
                    sortConfig={sortConfig} 
                    onSort={toggleSort}
                    filterValue={columnFilters.name}
                    onFilterChange={(val) => setTextFilter('name', val)}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'name')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.employer }}
                >
                  <TextFilterHeader 
                    column="employer" 
                    label="Employer" 
                    sortConfig={sortConfig} 
                    onSort={toggleSort}
                    filterValue={columnFilters.employer}
                    onFilterChange={(val) => setTextFilter('employer', val)}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'employer')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.title }}
                >
                  <TextFilterHeader 
                    column="title" 
                    label="Title" 
                    sortConfig={sortConfig} 
                    onSort={toggleSort}
                    filterValue={columnFilters.title}
                    onFilterChange={(val) => setTextFilter('title', val)}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'title')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.status }}
                >
                  <FilterableHeader
                    column="status"
                    label="Status"
                    sortConfig={sortConfig}
                    onSort={toggleSort}
                    filterValues={columnFilters.status}
                    onFilter={(val) => toggleFilter('status', val)}
                    filterOptions={[
                      { value: 'new', label: 'New' },
                      { value: 'outreached', label: 'Outreached' },
                      { value: 'scheduled', label: 'Scheduled' },
                      { value: 'completed', label: 'Completed' },
                      { value: 'passed', label: 'Passed' },
                    ]}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'status')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.conflict }}
                >
                  <FilterableHeader
                    column="conflict"
                    label="Conflict"
                    sortConfig={sortConfig}
                    onSort={toggleSort}
                    filterValues={columnFilters.conflict}
                    onFilter={(val) => toggleFilter('conflict', val)}
                    filterOptions={[
                      { value: 'none', label: 'None' },
                      { value: 'cleared', label: 'Cleared' },
                      { value: 'pending', label: 'Pending' },
                      { value: 'conflict', label: 'Conflict' },
                    ]}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'conflict')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.interviewDate }}
                >
                  <DateRangeFilterHeader 
                    column="interviewDate" 
                    label="Interview Date" 
                    sortConfig={sortConfig} 
                    onSort={toggleSort}
                    fromValue={columnFilters.interviewDateFrom}
                    toValue={columnFilters.interviewDateTo}
                    onFromChange={(val) => setDateFilter('interviewDateFrom', val)}
                    onToChange={(val) => setDateFilter('interviewDateTo', val)}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'interviewDate')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.lead }}
                >
                  <TextFilterHeader 
                    column="lead" 
                    label="Lead" 
                    sortConfig={sortConfig} 
                    onSort={toggleSort}
                    filterValue={columnFilters.lead}
                    onFilterChange={(val) => setTextFilter('lead', val)}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'lead')}
                  />
                </TableHead>
                <TableHead 
                  className="relative overflow-hidden" 
                  style={{ width: columnWidths.screening }}
                >
                  <FilterableHeader
                    column="screening"
                    label="AI Screening"
                    sortConfig={sortConfig}
                    onSort={toggleSort}
                    filterValues={columnFilters.screening}
                    onFilter={(val) => toggleFilter('screening', val)}
                    filterOptions={[
                      { value: 'strong', label: 'Strong' },
                      { value: 'mixed', label: 'Mixed' },
                      { value: 'weak', label: 'Weak' },
                      { value: 'none', label: 'Not screened' },
                    ]}
                  />
                  <div 
                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-purple-400 active:bg-purple-500"
                    onMouseDown={(e) => handleResizeStart(e, 'screening')}
                  />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredExperts.map((expert) => (
                <ExpertRow
                  key={expert.id}
                  expert={expert}
                  onUpdate={handleUpdate}
                  projectId={projectId!}
                  onScreeningComplete={() => refetch()}
                  onViewDetails={() => setSelectedExpertId(expert.id)}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Expert Detail Panel */}
      <ExpertDetailPanel
        expertId={selectedExpertId}
        expert={selectedExpert}
        open={!!selectedExpertId}
        onClose={() => setSelectedExpertId(null)}
      />
    </div>
  )
}

function ExpertRow({
  expert,
  onUpdate,
  projectId,
  onScreeningComplete,
  onViewDetails,
}: {
  expert: Expert
  onUpdate: (expertId: string, field: keyof Expert, value: any) => Promise<void>
  projectId: string
  onScreeningComplete?: () => void
  onViewDetails?: () => void
}) {
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState(expert.canonicalName)
  const screenExpert = useScreenExpert()
  const [showScreeningDetail, setShowScreeningDetail] = useState(false)

  const handleNameSave = async () => {
    if (editedName !== expert.canonicalName) {
      await onUpdate(expert.id, 'canonicalName', editedName)
    }
    setIsEditingName(false)
  }

  const handleStatusChange = async (status: ExpertStatus) => {
    await onUpdate(expert.id, 'status', status)
  }

  const handleConflictChange = async (conflictStatus: string) => {
    await onUpdate(expert.id, 'conflictStatus', conflictStatus === 'none' ? null : conflictStatus)
  }

  const handleDateChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    await onUpdate(expert.id, 'interviewDate', e.target.value || null)
  }

  return (
    <TableRow className="group">
      {/* View Details Button */}
      <TableCell className="p-2 overflow-hidden">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 opacity-50 group-hover:opacity-100"
          onClick={onViewDetails}
          title="View expert details & sources"
          aria-label="View expert details and sources"
        >
          <Eye className="w-4 h-4" />
        </Button>
      </TableCell>

      {/* Name */}
      <TableCell className="overflow-hidden">
        {isEditingName ? (
          <Input
            value={editedName}
            onChange={(e) => setEditedName(e.target.value)}
            onBlur={handleNameSave}
            onKeyDown={(e) => e.key === 'Enter' && handleNameSave()}
            autoFocus
            className="h-8"
          />
        ) : (
          <div
            className="cursor-pointer hover:underline hover:text-purple-600 truncate"
            onClick={onViewDetails}
            title={expert.canonicalName}
          >
            {expert.canonicalName}
          </div>
        )}
      </TableCell>

      {/* Employer */}
      <TableCell className="text-sm text-gray-600 overflow-hidden">
        <span className="block truncate" title={expert.canonicalEmployer || '-'}>
          {expert.canonicalEmployer || '-'}
        </span>
      </TableCell>

      {/* Title */}
      <TableCell className="text-sm text-gray-600 overflow-hidden">
        <span className="block truncate" title={expert.canonicalTitle || '-'}>
          {expert.canonicalTitle || '-'}
        </span>
      </TableCell>

      {/* Status */}
      <TableCell className="overflow-hidden">
        <Select value={expert.status} onValueChange={handleStatusChange}>
          <SelectTrigger className="h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="recommended">Recommended</SelectItem>
            <SelectItem value="awaiting_screeners">Awaiting Screeners</SelectItem>
            <SelectItem value="shortlisted">Shortlisted</SelectItem>
            <SelectItem value="requested">Requested</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="declined">Declined</SelectItem>
            <SelectItem value="conflict">Conflict</SelectItem>
          </SelectContent>
        </Select>
      </TableCell>

      {/* Conflict Status */}
      <TableCell className="overflow-hidden">
        <Select
          value={expert.conflictStatus || 'none'}
          onValueChange={handleConflictChange}
        >
          <SelectTrigger className="h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            <SelectItem value="cleared">Cleared</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="conflict">Conflict</SelectItem>
          </SelectContent>
        </Select>
      </TableCell>

      {/* Interview Date */}
      <TableCell className="overflow-hidden">
        <Input
          type="date"
          value={expert.interviewDate?.split('T')[0] || ''}
          onChange={handleDateChange}
          className="h-8"
        />
      </TableCell>

      {/* Lead Interviewer */}
      <TableCell className="overflow-hidden">
        <Input
          value={expert.leadInterviewer || ''}
          onChange={(e) => onUpdate(expert.id, 'leadInterviewer', e.target.value || null)}
          placeholder="Name"
          className="h-8"
        />
      </TableCell>

      {/* Smart Screening */}
      <TableCell className="overflow-hidden">
        {expert.aiScreeningGrade ? (
          <div className="flex items-center gap-2">
            <Badge
              variant={
                expert.aiScreeningGrade === 'strong'
                  ? 'default'
                  : expert.aiScreeningGrade === 'mixed'
                    ? 'secondary'
                    : 'outline'
              }
              className={`cursor-pointer hover:opacity-80 ${
                expert.aiScreeningGrade === 'strong' 
                  ? 'bg-green-600' 
                  : expert.aiScreeningGrade === 'mixed' 
                    ? 'bg-yellow-500' 
                    : 'bg-red-500 text-white'
              }`}
              onClick={() => setShowScreeningDetail(true)}
            >
              {expert.aiScreeningGrade}
              {expert.aiScreeningScore !== null && (
                <span className="ml-1 opacity-70">({expert.aiScreeningScore})</span>
              )}
            </Badge>
            {expert.aiScreeningMissingInfo && (
              <span className="text-xs text-amber-500" title="Missing information">!</span>
            )}
          </div>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-purple-600 hover:text-purple-700 hover:bg-purple-50"
            onClick={async () => {
              try {
                await screenExpert.mutateAsync({ expertId: expert.id, projectId })
                onScreeningComplete?.()
              } catch (error) {
                console.error('Screening failed:', error)
              }
            }}
            disabled={screenExpert.isPending}
          >
            {screenExpert.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-3 h-3 mr-1" />
                Screen
              </>
            )}
          </Button>
        )}

        {/* Screening Detail Modal */}
        <ScreeningDetailModal
          open={showScreeningDetail}
          onOpenChange={setShowScreeningDetail}
          expert={expert}
        />
      </TableCell>
    </TableRow>
  )
}

/**
 * Sortable Column Header
 */
function SortableHeader({
  column,
  label,
  sortConfig,
  onSort,
  className,
}: {
  column: string
  label: string
  sortConfig: { column: string | null; direction: 'asc' | 'desc' }
  onSort: (column: string) => void
  className?: string
}) {
  const isActive = sortConfig.column === column
  
  return (
    <TableHead className={className}>
      <button
        onClick={() => onSort(column)}
        className="flex items-center gap-1 hover:text-gray-900 transition-colors w-full text-left"
      >
        {label}
        {isActive ? (
          sortConfig.direction === 'asc' ? (
            <ArrowUp className="w-3 h-3 text-purple-600" />
          ) : (
            <ArrowDown className="w-3 h-3 text-purple-600" />
          )
        ) : (
          <ArrowUpDown className="w-3 h-3 text-gray-400" />
        )}
      </button>
    </TableHead>
  )
}

/**
 * Filterable Column Header with Sort + Filter
 */
function FilterableHeader({
  column,
  label,
  sortConfig,
  onSort,
  filterValues,
  onFilter,
  filterOptions,
}: {
  column: string
  label: string
  sortConfig: { column: string | null; direction: 'asc' | 'desc' }
  onSort: (column: string) => void
  filterValues: string[]
  onFilter: (value: string) => void
  filterOptions: { value: string; label: string }[]
}) {
  const [showFilter, setShowFilter] = useState(false)
  const isActive = sortConfig.column === column
  const hasFilter = filterValues.length > 0
  
  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <button
          onClick={() => onSort(column)}
          className="flex items-center gap-1 hover:text-gray-900 transition-colors"
        >
          {label}
          {isActive ? (
            sortConfig.direction === 'asc' ? (
              <ArrowUp className="w-3 h-3 text-purple-600" />
            ) : (
              <ArrowDown className="w-3 h-3 text-purple-600" />
            )
          ) : (
            <ArrowUpDown className="w-3 h-3 text-gray-400" />
          )}
        </button>
        <button
          onClick={() => setShowFilter(!showFilter)}
          className={`p-0.5 rounded hover:bg-gray-100 ${hasFilter ? 'text-purple-600' : 'text-gray-400'}`}
        >
          <Filter className="w-3 h-3" />
          {hasFilter && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-600 rounded-full" />
          )}
        </button>
      </div>
      
      {showFilter && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setShowFilter(false)} 
          />
          <div className="absolute top-full left-0 mt-1 z-20 bg-white border rounded-lg shadow-lg p-2 min-w-[140px]">
            {filterOptions.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded cursor-pointer text-sm"
              >
                <Checkbox
                  checked={filterValues.includes(opt.value)}
                  onCheckedChange={() => onFilter(opt.value)}
                  className="w-4 h-4"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Text Filter Header - Column header with text search filter
 */
function TextFilterHeader({
  column,
  label,
  sortConfig,
  onSort,
  filterValue,
  onFilterChange,
  className,
}: {
  column: string
  label: string
  sortConfig: { column: string | null; direction: 'asc' | 'desc' }
  onSort: (column: string) => void
  filterValue: string
  onFilterChange: (value: string) => void
  className?: string
}) {
  const [showFilter, setShowFilter] = useState(false)
  const isSorted = sortConfig.column === column
  const hasFilter = filterValue.length > 0
  
  return (
    <div className={`relative ${className}`}>
      <div className="flex items-center gap-1">
        <span className="text-xs font-medium truncate">{label}</span>
        <button
          onClick={() => onSort(column)}
          className={`p-0.5 rounded hover:bg-gray-100 ${isSorted ? 'text-purple-600' : 'text-gray-400'}`}
        >
          {isSorted ? (
            sortConfig.direction === 'asc' ? (
              <ArrowUp className="w-3 h-3 text-purple-600" />
            ) : (
              <ArrowDown className="w-3 h-3 text-purple-600" />
            )
          ) : (
            <ArrowUpDown className="w-3 h-3 text-gray-400" />
          )}
        </button>
        <button
          onClick={() => setShowFilter(!showFilter)}
          className={`p-0.5 rounded hover:bg-gray-100 relative ${hasFilter ? 'text-purple-600' : 'text-gray-400'}`}
        >
          <Filter className="w-3 h-3" />
          {hasFilter && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-600 rounded-full" />
          )}
        </button>
      </div>
      
      {showFilter && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowFilter(false)}
          />
          <div className="absolute top-full left-0 mt-1 bg-white border rounded-md shadow-lg p-2 z-20 min-w-[160px]">
            <Input
              type="text"
              placeholder={`Filter ${label.toLowerCase()}...`}
              value={filterValue}
              onChange={(e) => onFilterChange(e.target.value)}
              className="h-7 text-xs"
              autoFocus
            />
            {hasFilter && (
              <button
                onClick={() => {
                  onFilterChange('')
                  setShowFilter(false)
                }}
                className="mt-2 text-xs text-gray-500 hover:text-gray-700"
              >
                Clear filter
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Date Range Filter Header - Column header with date range filter (before/after)
 */
function DateRangeFilterHeader({
  column,
  label,
  sortConfig,
  onSort,
  fromValue,
  toValue,
  onFromChange,
  onToChange,
  className,
}: {
  column: string
  label: string
  sortConfig: { column: string | null; direction: 'asc' | 'desc' }
  onSort: (column: string) => void
  fromValue: string
  toValue: string
  onFromChange: (value: string) => void
  onToChange: (value: string) => void
  className?: string
}) {
  const [showFilter, setShowFilter] = useState(false)
  const isSorted = sortConfig.column === column
  const hasFilter = fromValue || toValue
  
  return (
    <div className={`relative ${className}`}>
      <div className="flex items-center gap-1">
        <span className="text-xs font-medium truncate">{label}</span>
        <button
          onClick={() => onSort(column)}
          className={`p-0.5 rounded hover:bg-gray-100 ${isSorted ? 'text-purple-600' : 'text-gray-400'}`}
        >
          {isSorted ? (
            sortConfig.direction === 'asc' ? (
              <ArrowUp className="w-3 h-3 text-purple-600" />
            ) : (
              <ArrowDown className="w-3 h-3 text-purple-600" />
            )
          ) : (
            <ArrowUpDown className="w-3 h-3 text-gray-400" />
          )}
        </button>
        <button
          onClick={() => setShowFilter(!showFilter)}
          className={`p-0.5 rounded hover:bg-gray-100 relative ${hasFilter ? 'text-purple-600' : 'text-gray-400'}`}
        >
          <Filter className="w-3 h-3" />
          {hasFilter && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-600 rounded-full" />
          )}
        </button>
      </div>
      
      {showFilter && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowFilter(false)}
          />
          <div className="absolute top-full left-0 mt-1 bg-white border rounded-md shadow-lg p-3 z-20 min-w-[200px]">
            <div className="space-y-2">
              <div>
                <label className="text-xs text-gray-500 block mb-1">From (after)</label>
                <Input
                  type="date"
                  value={fromValue}
                  onChange={(e) => onFromChange(e.target.value)}
                  className="h-7 text-xs"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">To (before)</label>
                <Input
                  type="date"
                  value={toValue}
                  onChange={(e) => onToChange(e.target.value)}
                  className="h-7 text-xs"
                />
              </div>
            </div>
            {hasFilter && (
              <button
                onClick={() => {
                  onFromChange('')
                  onToChange('')
                  setShowFilter(false)
                }}
                className="mt-3 text-xs text-gray-500 hover:text-gray-700"
              >
                Clear dates
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Screener Config Dialog - Configure screener questions and rubric
 */
function ScreenerConfigDialog({
  open,
  onOpenChange,
  questions,
  onQuestionsChange,
  autoScreen,
  onAutoScreenChange,
  onSave,
  isSaving,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  questions: ScreenerQuestion[]
  onQuestionsChange: (questions: ScreenerQuestion[]) => void
  autoScreen: boolean
  onAutoScreenChange: (enabled: boolean) => void
  onSave: () => void
  isSaving: boolean
}) {
  const addQuestion = () => {
    onQuestionsChange([
      ...questions,
      {
        id: `q${Date.now()}`,
        order: questions.length + 1,
        text: '',
        idealAnswer: '',
        redFlags: '',
      },
    ])
  }

  const updateQuestion = (index: number, field: keyof ScreenerQuestion, value: any) => {
    const updated = [...questions]
    updated[index] = { ...updated[index], [field]: value }
    onQuestionsChange(updated)
  }

  const removeQuestion = (index: number) => {
    onQuestionsChange(questions.filter((_, i) => i !== index))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Screener Configuration</DialogTitle>
          <DialogDescription>
            Define screener questions and ideal answers. The AI will use this rubric to assess experts.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Auto-Screen Toggle */}
          <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-100">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-purple-600" />
              <div>
                <p className="font-medium text-purple-900">Auto-Screen on Ingest</p>
                <p className="text-sm text-purple-600">Automatically run AI screening after each email ingestion</p>
              </div>
            </div>
            <Checkbox
              checked={autoScreen}
              onCheckedChange={(checked) => onAutoScreenChange(checked === true)}
              className="data-[state=checked]:bg-purple-600"
            />
          </div>

          <div className="border-t pt-4">
            <p className="font-medium text-gray-700 mb-3">Screener Questions</p>
          </div>

          {questions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No screener questions configured.</p>
              <p className="text-sm mt-1">Add questions to enable detailed rubric-based screening.</p>
            </div>
          ) : (
            questions.map((q, index) => (
              <div key={q.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm text-gray-500">Question {index + 1}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeQuestion(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-2">
                  <Label>Question</Label>
                  <Input
                    value={q.text}
                    onChange={(e) => updateQuestion(index, 'text', e.target.value)}
                    placeholder="e.g., What is your experience with retail analytics?"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Ideal Answer</Label>
                  <Textarea
                    value={q.idealAnswer}
                    onChange={(e) => updateQuestion(index, 'idealAnswer', e.target.value)}
                    placeholder="Describe what a strong answer looks like..."
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Weight (1-3)</Label>
                    <Select
                      value={String(q.order || 1)}
                      onValueChange={(v) => updateQuestion(index, 'order', parseInt(v))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 - Standard</SelectItem>
                        <SelectItem value="2">2 - Important</SelectItem>
                        <SelectItem value="3">3 - Critical</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Red Flags (comma separated)</Label>
                    <Input
                      value={q.redFlags || ''}
                      onChange={(e) => updateQuestion(index, 'redFlags', e.target.value)}
                      placeholder="e.g., no experience, competitor"
                    />
                  </div>
                </div>
              </div>
            ))
          )}

          <Button variant="outline" onClick={addQuestion} className="w-full">
            <Plus className="w-4 h-4 mr-2" />
            Add Question
          </Button>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSave} disabled={isSaving}>
            {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Screening Detail Modal - Shows detailed screening assessment
 */
function ScreeningDetailModal({
  open,
  onOpenChange,
  expert,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  expert: Expert
}) {
  // Parse missing info if it's a JSON string
  const missingInfo = expert.aiScreeningMissingInfo 
    ? (typeof expert.aiScreeningMissingInfo === 'string' 
        ? JSON.parse(expert.aiScreeningMissingInfo) 
        : expert.aiScreeningMissingInfo)
    : null

  const gradeColor = expert.aiScreeningGrade === 'strong' 
    ? 'text-green-600 bg-green-50 border-green-200' 
    : expert.aiScreeningGrade === 'mixed' 
      ? 'text-yellow-600 bg-yellow-50 border-yellow-200' 
      : 'text-red-600 bg-red-50 border-red-200'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-600" />
            Smart Fit Assessment
          </DialogTitle>
          <DialogDescription>
            AI assessment for {expert.canonicalName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Grade and Score */}
          <div className={`rounded-lg border p-4 ${gradeColor}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium opacity-70">Overall Grade</p>
                <p className="text-2xl font-bold capitalize">{expert.aiScreeningGrade}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium opacity-70">Score</p>
                <p className="text-3xl font-bold">{expert.aiScreeningScore}</p>
              </div>
            </div>
            {expert.aiScreeningConfidence && (
              <p className="text-sm mt-2 opacity-70">
                Confidence: <span className="capitalize">{expert.aiScreeningConfidence}</span>
              </p>
            )}
          </div>

          {/* Rationale */}
          {expert.aiScreeningRationale && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">Assessment Rationale</p>
              <p className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3">
                {expert.aiScreeningRationale}
              </p>
            </div>
          )}

          {/* Missing Info */}
          {missingInfo && missingInfo.length > 0 && (
            <div>
              <p className="text-sm font-medium text-amber-700 mb-1 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                Missing Information
              </p>
              <ul className="text-sm text-amber-600 bg-amber-50 rounded-lg p-3 list-disc list-inside">
                {missingInfo.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Expert Summary */}
          <div className="border-t pt-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Expert Profile</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">Employer:</span>
                <span className="ml-1">{expert.canonicalEmployer || 'Unknown'}</span>
              </div>
              <div>
                <span className="text-gray-500">Title:</span>
                <span className="ml-1">{expert.canonicalTitle || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
