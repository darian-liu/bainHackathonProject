/**
 * Ingest Page - Extract experts from emails
 * Uses auto-ingest for streamlined workflow
 */

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Loader2, CheckCircle2, AlertCircle, ArrowRight, Sparkles, Mail, Settings, Inbox, FileText } from 'lucide-react'
import { useAutoIngest, useProject, useScreenAllExperts, useAutoScanInbox } from './api'
import { useQuery } from '@tanstack/react-query'
import { outlookApi } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import type { AutoIngestResult } from './types'

export function IngestPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const autoIngest = useAutoIngest()
  const autoScanInbox = useAutoScanInbox()
  const { data: projectData } = useProject(projectId!)
  const screenAllExperts = useScreenAllExperts()

  const [ingestMode, setIngestMode] = useState<'select' | 'paste' | 'scanning'>('select')
  const [emailText, setEmailText] = useState('')
  const [network, setNetwork] = useState<string>('')
  const [result, setResult] = useState<AutoIngestResult | null>(null)
  const [isAutoScreening, setIsAutoScreening] = useState(false)
  const [screeningResult, setScreeningResult] = useState<{
    screened: number
    failed: number
  } | null>(null)

  const autoScreenEnabled = projectData?.screenerConfig?.autoScreen || false

  // Outlook connection status
  const { data: outlookStatus } = useQuery({
    queryKey: ['outlook-status'],
    queryFn: outlookApi.getStatus,
  })

  const handleIngest = async () => {
    if (!projectId || !emailText.trim()) return

    try {
      const ingestResult = await autoIngest.mutateAsync({
        projectId,
        emailText,
        network: network || undefined,
      })
      setResult(ingestResult)

      // Auto-screen if enabled and there were added/updated experts
      if (autoScreenEnabled && (ingestResult.summary.addedCount > 0 || ingestResult.summary.updatedCount > 0)) {
        setIsAutoScreening(true)
        try {
          const screenResult = await screenAllExperts.mutateAsync({ projectId })
          setScreeningResult({ screened: screenResult.screened, failed: screenResult.failed })
        } catch (error) {
          console.error('Auto-screening failed:', error)
        } finally {
          setIsAutoScreening(false)
        }
      }
    } catch (error) {
      console.error('Ingestion failed:', error)
    }
  }

  // handleUndo removed - undo was fundamentally broken
  // Users should use delete from the tracker page instead

  const handleAutoScan = async () => {
    if (!projectId) return

    console.log(`[SCAN UI] IngestPage: Starting auto-scan for project ${projectId}`)
    setIngestMode('scanning')

    try {
      // Navigate to tracker immediately with scanning state
      console.log(`[SCAN UI] IngestPage: Navigating to tracker with scanning=true`)
      navigate(`/expert-networks/${projectId}/tracker?scanning=true`)

      // Start the scan (this will be picked up by TrackerPage)
      console.log(`[SCAN UI] IngestPage: Calling autoScanInbox with maxEmails=50`)
      await autoScanInbox.mutateAsync({ projectId, maxEmails: 50 })
      console.log(`[SCAN UI] IngestPage: Auto-scan completed successfully`)
    } catch (error) {
      console.error(`[SCAN UI] IngestPage: Auto-scan failed:`, error)
      // Navigate back with error
      navigate(`/expert-networks/${projectId}/ingest?scan_error=true`)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-purple-600" />
            AI Extract & Screen
          </h1>
          <p className="text-gray-600">
            Ingest expert network emails. AI extracts experts, validates data, and runs smart screening.
          </p>
        </div>
        {/* Outlook Connection Status */}
        <div className="flex items-center gap-2 text-sm">
          <Mail className="w-4 h-4" />
          {outlookStatus?.connected ? (
            <span className="text-green-600">Outlook: {outlookStatus.userEmail}</span>
          ) : (
            <Link to="/settings" className="text-muted-foreground hover:text-blue-600 flex items-center gap-1">
              <Settings className="w-3 h-3" />
              Connect Outlook
            </Link>
          )}
        </div>
      </div>

      {!result && ingestMode === 'select' ? (
        /* Ingestion Mode Selection */
        <div className="grid md:grid-cols-2 gap-4">
          {/* Auto-scan Inbox Option */}
          <Card
            className={`cursor-pointer transition-all hover:border-purple-400 hover:shadow-md ${!outlookStatus?.connected ? 'opacity-60' : ''
              }`}
            onClick={() => outlookStatus?.connected && handleAutoScan()}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Inbox className="w-5 h-5 text-purple-600" />
                Auto-scan Inbox
                <Badge variant="secondary" className="ml-2">Recommended</Badge>
              </CardTitle>
              <CardDescription>
                Scans recent Outlook emails from expert networks (AlphaSights, Guidepoint, GLG, etc.).
                May take a moment.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {outlookStatus?.connected ? (
                <Button
                  className="w-full"
                  onClick={(e) => { e.stopPropagation(); handleAutoScan(); }}
                  disabled={autoScanInbox.isPending}
                >
                  {autoScanInbox.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Starting scan...
                    </>
                  ) : (
                    <>
                      <Inbox className="w-4 h-4 mr-2" />
                      Scan Inbox Now
                    </>
                  )}
                </Button>
              ) : (
                <Link to="/settings">
                  <Button variant="outline" className="w-full">
                    <Settings className="w-4 h-4 mr-2" />
                    Connect Outlook First
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>

          {/* Manual Paste Option */}
          <Card
            className="cursor-pointer transition-all hover:border-blue-400 hover:shadow-md"
            onClick={() => setIngestMode('paste')}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Paste Email Manually
              </CardTitle>
              <CardDescription>
                Copy and paste email content directly. Works with any email source.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                onClick={(e) => { e.stopPropagation(); setIngestMode('paste'); }}
              >
                <FileText className="w-4 h-4 mr-2" />
                Paste Email
              </Button>
            </CardContent>
          </Card>
        </div>
      ) : !result && ingestMode === 'paste' ? (
        /* Manual Paste Mode */
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Paste Email Content</CardTitle>
                <CardDescription>
                  Paste emails from AlphaSights, Guidepoint, GLG, or other expert networks.
                  AI will extract expert profiles, validate data, deduplicate, and run smart screening.
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setIngestMode('select')}>
                ← Back
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="network">Network (Optional)</Label>
              <Select value={network} onValueChange={setNetwork}>
                <SelectTrigger>
                  <SelectValue placeholder="Auto-detect network" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="alphasights">AlphaSights</SelectItem>
                  <SelectItem value="guidepoint">Guidepoint</SelectItem>
                  <SelectItem value="glg">GLG</SelectItem>
                  <SelectItem value="tegus">Tegus</SelectItem>
                  <SelectItem value="thirdbridge">Third Bridge</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email Content</Label>
              <Textarea
                id="email"
                placeholder="Paste email content here..."
                value={emailText}
                onChange={(e) => setEmailText(e.target.value)}
                rows={15}
                className="font-mono text-sm"
              />
            </div>

            <Button
              onClick={handleIngest}
              disabled={!emailText.trim() || autoIngest.isPending}
              className="w-full"
            >
              {autoIngest.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  AI Processing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  AI Extract & Screen
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      ) : result ? (
        <div className="space-y-4">
          {/* No-Op Summary (duplicate/repeated content) */}
          {result.summary.isNoOp ? (
            <Card className="border-gray-200 bg-gray-50">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-gray-500" />
                  <CardTitle className="text-gray-700">No Changes Detected</CardTitle>
                </div>
                <CardDescription className="text-gray-600">
                  {result.summary.extractedCount} expert(s) found, but all match existing records with no new information.
                  {result.summary.network && ` (${result.summary.network})`}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Notes explaining why it's a no-op */}
                {result.summary.extractionNotes && result.summary.extractionNotes.length > 0 && (
                  <div className="space-y-2 text-sm text-gray-600 bg-white p-3 rounded-lg border">
                    <ul className="list-disc list-inside space-y-1">
                      {result.summary.extractionNotes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <Button onClick={() => navigate(`/expert-networks/${projectId}/tracker`)}>
                    View Tracker
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setResult(null)
                      setEmailText('')
                    }}
                  >
                    Ingest Another
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Success Summary with actual changes */
            <Card className="border-green-200 bg-green-50">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  <CardTitle className="text-green-900">Ingestion Complete</CardTitle>
                </div>
                <CardDescription className="text-green-700">
                  {result.summary.extractedCount} experts extracted from email
                  {result.summary.network && ` (${result.summary.network})`}
                </CardDescription>
              </CardHeader>

              {/* Auto-Screening Status */}
              {(isAutoScreening || screeningResult) && (
                <div className={`mx-6 mb-4 p-3 rounded-lg flex items-center gap-3 ${isAutoScreening ? 'bg-purple-100 border border-purple-200' : 'bg-purple-50 border border-purple-100'}`}>
                  {isAutoScreening ? (
                    <>
                      <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                      <div>
                        <p className="font-medium text-purple-800">Running AI Screening...</p>
                        <p className="text-sm text-purple-600">Evaluating experts against project needs</p>
                      </div>
                    </>
                  ) : screeningResult && (
                    <>
                      <Sparkles className="w-5 h-5 text-purple-600" />
                      <div>
                        <p className="font-medium text-purple-800">AI Screening Complete</p>
                        <p className="text-sm text-purple-600">
                          {screeningResult.screened} expert(s) screened
                          {screeningResult.failed > 0 && `, ${screeningResult.failed} failed`}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              )}
              <CardContent className="space-y-4">
                {/* Change Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <SummaryCard
                    label="Added"
                    count={result.summary.addedCount}
                    variant="success"
                  />
                  <SummaryCard
                    label="Updated"
                    count={result.summary.updatedCount}
                    variant="info"
                  />
                  <SummaryCard
                    label="Merged"
                    count={result.summary.mergedCount}
                    variant="info"
                  />
                  <SummaryCard
                    label="Needs Review"
                    count={result.summary.needsReviewCount}
                    variant={result.summary.needsReviewCount > 0 ? 'warning' : 'default'}
                  />
                </div>

                {/* Details */}
                {result.changes.added.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-gray-700">New Experts Added:</h4>
                    <div className="flex flex-wrap gap-2">
                      {result.changes.added.map((change, idx) => (
                        <Badge key={idx} variant="secondary">
                          {change.expertName}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {result.changes.updated.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-gray-700">Experts Updated:</h4>
                    <div className="flex flex-wrap gap-2">
                      {result.changes.updated.map((change, idx) => (
                        <Badge key={idx} variant="outline">
                          {change.expertName}
                          {change.fieldsUpdated && change.fieldsUpdated.length > 0 && (
                            <span className="ml-1 text-gray-500">
                              ({change.fieldsUpdated.join(', ')})
                            </span>
                          )}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {result.changes.merged.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm text-gray-700">Duplicates Merged:</h4>
                    <ul className="text-sm text-gray-600 space-y-1">
                      {result.changes.merged.map((change, idx) => (
                        <li key={idx}>
                          Auto-merged duplicate (score: {Math.round(change.score! * 100)}%)
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.changes.needsReview.length > 0 && (
                  <div className="space-y-2 bg-amber-50 p-3 rounded-lg border border-amber-200">
                    <h4 className="font-medium text-sm text-amber-800 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      Items Needing Review:
                    </h4>
                    <ul className="text-sm text-amber-700 space-y-1">
                      {result.changes.needsReview.map((change, idx) => (
                        <li key={idx}>{change.reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.summary.extractionNotes && result.summary.extractionNotes.length > 0 && (
                  <div className="space-y-2 text-sm text-gray-600">
                    <h4 className="font-medium">Notes:</h4>
                    <ul className="list-disc list-inside">
                      {result.summary.extractionNotes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 pt-4">
                  <Button onClick={() => navigate(`/expert-networks/${projectId}/tracker`)}>
                    View Tracker
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setResult(null)
                      setEmailText('')
                    }}
                  >
                    Ingest Another
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : null}
    </div>
  )
}

function SummaryCard({
  label,
  count,
  variant = 'default',
}: {
  label: string
  count: number
  variant?: 'default' | 'success' | 'info' | 'warning'
}) {
  const bgColors = {
    default: 'bg-gray-100',
    success: 'bg-green-100',
    info: 'bg-blue-100',
    warning: 'bg-amber-100',
  }
  const textColors = {
    default: 'text-gray-900',
    success: 'text-green-900',
    info: 'text-blue-900',
    warning: 'text-amber-900',
  }

  return (
    <div className={`${bgColors[variant]} rounded-lg p-3 text-center`}>
      <div className={`text-2xl font-bold ${textColors[variant]}`}>{count}</div>
      <div className={`text-sm ${textColors[variant]} opacity-80`}>{label}</div>
    </div>
  )
}
