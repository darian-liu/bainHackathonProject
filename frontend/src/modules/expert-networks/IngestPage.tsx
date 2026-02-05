/**
 * Ingest Page - Extract experts from emails
 * Uses auto-ingest for streamlined workflow
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, CheckCircle2, AlertCircle, ArrowRight, Undo2, Sparkles } from 'lucide-react'
import { useAutoIngest, useUndoIngestion, useProject, useScreenAllExperts } from './api'
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
  const undoIngestion = useUndoIngestion()
  const { data: projectData } = useProject(projectId!)
  const screenAllExperts = useScreenAllExperts()

  const [emailText, setEmailText] = useState('')
  const [network, setNetwork] = useState<string>('')
  const [result, setResult] = useState<AutoIngestResult | null>(null)
  const [isAutoScreening, setIsAutoScreening] = useState(false)
  const [screeningResult, setScreeningResult] = useState<{
    screened: number
    failed: number
  } | null>(null)

  const autoScreenEnabled = projectData?.screenerConfig?.autoScreen || false

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

  const handleUndo = async () => {
    if (!projectId || !result) return

    try {
      await undoIngestion.mutateAsync({
        projectId,
        logId: result.ingestionLogId,
      })
      setResult(null)
      setEmailText('')
    } catch (error) {
      console.error('Undo failed:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-purple-600" />
          AI Extract & Screen
        </h1>
        <p className="text-gray-600">
          Paste expert network emails. AI extracts experts, validates data, and runs smart screening.
        </p>
      </div>

      {!result ? (
        <Card>
          <CardHeader>
            <CardTitle>Paste Email Content</CardTitle>
            <CardDescription>
              Paste emails from AlphaSights, Guidepoint, GLG, or other expert networks.
              AI will extract expert profiles, validate data, deduplicate, and run smart screening.
            </CardDescription>
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
      ) : (
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
                  <Button
                    variant="outline"
                    onClick={handleUndo}
                    disabled={undoIngestion.isPending}
                  >
                    {undoIngestion.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Undo2 className="w-4 h-4 mr-2" />
                    )}
                    Undo Ingestion
                  </Button>
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
      )}
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
