/**
 * Ingest Page - Extract experts from emails
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { useExtractEmail, useCommitExperts } from './api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import type { EmailExtractionResult, ExtractedExpert } from './types'

export function IngestPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const extractEmail = useExtractEmail()
  const commitExperts = useCommitExperts()

  const [emailText, setEmailText] = useState('')
  const [network, setNetwork] = useState<string>('')
  const [extractionResult, setExtractionResult] = useState<EmailExtractionResult | null>(null)
  const [selectedIndices, setSelectedIndices] = useState<number[]>([])

  const handleExtract = async () => {
    if (!projectId || !emailText.trim()) return

    try {
      const result = await extractEmail.mutateAsync({
        projectId,
        emailText,
        network: network || undefined,
      })
      setExtractionResult(result)
      // Select all experts by default
      setSelectedIndices(result.result.experts.map((_, idx) => idx))
    } catch (error) {
      console.error('Extraction failed:', error)
    }
  }

  const handleCommit = async () => {
    if (!projectId || !extractionResult) return

    try {
      await commitExperts.mutateAsync({
        projectId,
        emailId: extractionResult.emailId,
        selectedIndices,
      })
      navigate(`/expert-networks/${projectId}/tracker`)
    } catch (error) {
      console.error('Commit failed:', error)
    }
  }

  const toggleExpert = (index: number) => {
    setSelectedIndices((prev) =>
      prev.includes(index)
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ingest Email</h1>
        <p className="text-gray-600">Extract expert profiles from email</p>
      </div>

      {!extractionResult ? (
        <Card>
          <CardHeader>
            <CardTitle>Paste Email Content</CardTitle>
            <CardDescription>
              Paste the email from AlphaSights, Guidepoint, GLG, etc.
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
              onClick={handleExtract}
              disabled={!emailText.trim() || extractEmail.isPending}
              className="w-full"
            >
              {extractEmail.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Extracting...
                </>
              ) : (
                'Extract Experts'
              )}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Extraction Results</CardTitle>
                  <CardDescription>
                    {extractionResult.result.experts.length} experts found
                    {extractionResult.result.inferredNetwork && (
                      <> from {extractionResult.result.inferredNetwork}</>
                    )}
                  </CardDescription>
                </div>
                <Button variant="outline" onClick={() => setExtractionResult(null)}>
                  Start Over
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                {extractionResult.result.experts.map((expert, idx) => (
                  <ExpertCard
                    key={idx}
                    expert={expert}
                    index={idx}
                    isSelected={selectedIndices.includes(idx)}
                    onToggle={toggleExpert}
                  />
                ))}
              </div>

              <Button
                onClick={handleCommit}
                disabled={selectedIndices.length === 0 || commitExperts.isPending}
                className="w-full"
              >
                {commitExperts.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Committing...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Commit {selectedIndices.length} Experts to Tracker
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

function ExpertCard({
  expert,
  index,
  isSelected,
  onToggle,
}: {
  expert: ExtractedExpert
  index: number
  isSelected: boolean
  onToggle: (index: number) => void
}) {
  return (
    <div className="border rounded-lg p-4 space-y-2">
      <div className="flex items-start gap-3">
        <Checkbox checked={isSelected} onCheckedChange={() => onToggle(index)} />
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{expert.fullName}</h3>
            <Badge variant={expert.overallConfidence === 'high' ? 'default' : 'secondary'}>
              {expert.overallConfidence} confidence
            </Badge>
          </div>

          {expert.employer && (
            <p className="text-sm text-gray-600">
              {expert.title ? `${expert.title} at ` : ''}
              {expert.employer}
            </p>
          )}

          {expert.relevanceBullets && expert.relevanceBullets.length > 0 && (
            <ul className="text-sm text-gray-700 list-disc list-inside">
              {expert.relevanceBullets.slice(0, 3).map((bullet, i) => (
                <li key={i}>{bullet}</li>
              ))}
            </ul>
          )}

          {expert.statusCue && (
            <div className="flex items-center gap-2 text-sm">
              {expert.statusCue === 'available' ? (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              ) : expert.statusCue === 'declined' ? (
                <AlertCircle className="w-4 h-4 text-red-600" />
              ) : null}
              <span className="text-gray-600">Status: {expert.statusCue}</span>
            </div>
          )}

          {expert.conflictStatus && (
            <Badge variant={expert.conflictStatus === 'cleared' ? 'default' : 'destructive'}>
              Conflict: {expert.conflictStatus}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}
