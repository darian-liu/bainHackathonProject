/**
 * Tracker Page - Main expert tracker table
 * Simplified MVP version focused on core functionality
 */

import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Loader2, Search, RefreshCw, ArrowLeft } from 'lucide-react'
import { useExperts, useUpdateExpert, useProject, expertNetworksApi } from './api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import type { Expert, ExpertStatus } from './types'

export function TrackerPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { data: projectData } = useProject(projectId!)
  const { data, isLoading, refetch } = useExperts(projectId!)
  const updateExpert = useUpdateExpert()

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [isExporting, setIsExporting] = useState(false)

  const experts = data?.experts || []

  // Filter and search experts
  const filteredExperts = useMemo(() => {
    let result = experts

    // Status filter
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

    return result
  }, [experts, statusFilter, searchQuery])

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

      {/* Filters */}
      <div className="flex gap-4">
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
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-48">Name</TableHead>
                <TableHead className="w-40">Employer</TableHead>
                <TableHead className="w-40">Title</TableHead>
                <TableHead className="w-36">Status</TableHead>
                <TableHead className="w-32">Conflict</TableHead>
                <TableHead className="w-36">Interview Date</TableHead>
                <TableHead className="w-32">Lead</TableHead>
                <TableHead className="w-32">AI Rec</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredExperts.map((expert) => (
                <ExpertRow
                  key={expert.id}
                  expert={expert}
                  onUpdate={handleUpdate}
                  projectId={projectId!}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

function ExpertRow({
  expert,
  onUpdate,
  projectId,
}: {
  expert: Expert
  onUpdate: (expertId: string, field: keyof Expert, value: any) => Promise<void>
  projectId: string
}) {
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState(expert.canonicalName)

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
    <TableRow>
      {/* Name */}
      <TableCell>
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
            className="cursor-pointer hover:underline"
            onClick={() => setIsEditingName(true)}
          >
            {expert.canonicalName}
          </div>
        )}
      </TableCell>

      {/* Employer */}
      <TableCell className="text-sm text-gray-600">
        {expert.canonicalEmployer || '-'}
      </TableCell>

      {/* Title */}
      <TableCell className="text-sm text-gray-600">
        {expert.canonicalTitle || '-'}
      </TableCell>

      {/* Status */}
      <TableCell>
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
      <TableCell>
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
      <TableCell>
        <Input
          type="date"
          value={expert.interviewDate?.split('T')[0] || ''}
          onChange={handleDateChange}
          className="h-8"
        />
      </TableCell>

      {/* Lead Interviewer */}
      <TableCell>
        <Input
          value={expert.leadInterviewer || ''}
          onChange={(e) => onUpdate(expert.id, 'leadInterviewer', e.target.value || null)}
          placeholder="Name"
          className="h-8"
        />
      </TableCell>

      {/* AI Recommendation */}
      <TableCell>
        {expert.aiRecommendation ? (
          <Badge
            variant={
              expert.aiRecommendation === 'strong_fit'
                ? 'default'
                : expert.aiRecommendation === 'maybe'
                  ? 'secondary'
                  : 'outline'
            }
            title={expert.aiRecommendationRationale || undefined}
          >
            {expert.aiRecommendation}
          </Badge>
        ) : (
          <span className="text-xs text-gray-400">-</span>
        )}
      </TableCell>
    </TableRow>
  )
}
