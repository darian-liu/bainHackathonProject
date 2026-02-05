import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Settings, Eye, EyeOff, Loader2, Check, RefreshCw, Mail, Link2, Unlink } from 'lucide-react'
import { settingsApi, outlookApi, type SettingsData } from '@/services/api'
import { useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface CredentialInputProps {
  label: string
  description: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  isSecret?: boolean
}

function CredentialInput({
  label,
  description,
  value,
  onChange,
  placeholder,
  isSecret = false,
}: CredentialInputProps) {
  const [showValue, setShowValue] = useState(false)

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-slate-700">{label}</label>
      <p className="text-xs text-muted-foreground">{description}</p>
      <div className="relative">
        <input
          type={isSecret && !showValue ? 'password' : 'text'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
        />
        {isSecret && (
          <button
            type="button"
            onClick={() => setShowValue(!showValue)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            {showValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  )
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState<Partial<SettingsData>>({})
  const [hasChanges, setHasChanges] = useState(false)
  const [outlookMessage, setOutlookMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Handle OAuth callback query params
  useEffect(() => {
    const connected = searchParams.get('outlook_connected')
    const error = searchParams.get('outlook_error')

    if (connected === 'true') {
      setOutlookMessage({ type: 'success', text: 'Outlook connected successfully!' })
      queryClient.invalidateQueries({ queryKey: ['outlook-status'] })
      // Clean up URL
      searchParams.delete('outlook_connected')
      setSearchParams(searchParams, { replace: true })
    } else if (error) {
      setOutlookMessage({ type: 'error', text: `Outlook connection failed: ${error}` })
      searchParams.delete('outlook_error')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams, queryClient])

  // Fetch current settings
  const { data: currentSettings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.getSettings,
  })

  // Save settings mutation
  const saveMutation = useMutation({
    mutationFn: settingsApi.updateSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setHasChanges(false)
      setFormData({})
    },
  })

  // Test connections mutation
  const testMutation = useMutation({
    mutationFn: settingsApi.testConnections,
  })

  // Outlook status query
  const { data: outlookStatus, isLoading: isLoadingOutlook } = useQuery({
    queryKey: ['outlook-status'],
    queryFn: outlookApi.getStatus,
  })

  // Outlook test mutation
  const outlookTestMutation = useMutation({
    mutationFn: outlookApi.testConnection,
    onSuccess: (data) => {
      if (data.success) {
        setOutlookMessage({ type: 'success', text: `Connection verified: ${data.userEmail}` })
        queryClient.invalidateQueries({ queryKey: ['outlook-status'] })
      } else {
        setOutlookMessage({ type: 'error', text: data.error || 'Test failed' })
      }
    },
  })

  // Outlook disconnect mutation
  const outlookDisconnectMutation = useMutation({
    mutationFn: outlookApi.disconnect,
    onSuccess: () => {
      setOutlookMessage({ type: 'success', text: 'Outlook disconnected' })
      queryClient.invalidateQueries({ queryKey: ['outlook-status'] })
    },
  })

  // Connect Outlook handler
  const handleConnectOutlook = async () => {
    try {
      // Auto-save if there are unsaved Outlook credentials
      if (hasChanges) {
        await saveMutation.mutateAsync(formData)
      }
      const { authUrl } = await outlookApi.getAuthUrl('/settings')
      window.location.href = authUrl
    } catch (error) {
      setOutlookMessage({ type: 'error', text: 'Failed to start OAuth flow. Check credentials.' })
    }
  }

  const handleFieldChange = (field: keyof SettingsData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setHasChanges(true)
  }

  const handleSave = () => {
    saveMutation.mutate(formData)
  }

  const handleTest = () => {
    testMutation.mutate()
  }

  const getDisplayValue = (field: keyof SettingsData): string => {
    if (formData[field] !== undefined) {
      return formData[field] as string
    }
    return currentSettings?.[field] || ''
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="w-8 h-8 text-slate-600" />
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Configure API credentials and preferences</p>
        </div>
      </div>

      {/* OpenAI / Portkey Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>OpenAI / Portkey Configuration</CardTitle>
          <CardDescription>
            Required for document embeddings, chat, and expert extraction. At Bain, use Portkey gateway with @personal-openai/ model prefix.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CredentialInput
            label="OpenAI API Key"
            description="Your OpenAI or Portkey API key"
            value={getDisplayValue('openai_api_key')}
            onChange={(v) => handleFieldChange('openai_api_key', v)}
            placeholder="sk-... or Portkey API key"
            isSecret
          />
          <CredentialInput
            label="OpenAI Base URL"
            description="Optional: Portkey or other OpenAI-compatible gateway URL (leave empty for direct OpenAI)"
            value={getDisplayValue('openai_base_url')}
            onChange={(v) => handleFieldChange('openai_base_url', v)}
            placeholder="https://api.portkey.ai/v1"
          />
          <CredentialInput
            label="OpenAI Model"
            description="Model to use (Bain: use @personal-openai/gpt-4o format for Portkey)"
            value={getDisplayValue('openai_model')}
            onChange={(v) => handleFieldChange('openai_model', v)}
            placeholder="@personal-openai/gpt-4o"
          />
        </CardContent>
      </Card>

      {/* Personal Outlook Integration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Personal Outlook Integration
          </CardTitle>
          <CardDescription>
            Connect your personal Outlook inbox for expert-network email ingestion.
            Required to automatically scan emails from AlphaSights, Guidepoint, GLG, etc.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CredentialInput
            label="Outlook Client ID"
            description="Azure App Registration Client ID (for personal accounts)"
            value={getDisplayValue('outlook_client_id')}
            onChange={(v) => handleFieldChange('outlook_client_id', v)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          />
          <CredentialInput
            label="Outlook Client Secret"
            description="Azure App Registration Client Secret"
            value={getDisplayValue('outlook_client_secret')}
            onChange={(v) => handleFieldChange('outlook_client_secret', v)}
            placeholder="Your client secret"
            isSecret
          />
          <CredentialInput
            label="Redirect URI"
            description="OAuth callback URL (must match Azure app registration)"
            value={getDisplayValue('outlook_redirect_uri')}
            onChange={(v) => handleFieldChange('outlook_redirect_uri', v)}
            placeholder="http://localhost:8000/api/outlook/callback"
          />
          <CredentialInput
            label="Allowed Sender Domains (Optional)"
            description="Comma-separated domains to filter emails (e.g., alphasights.com, guidepoint.com, glg.it)"
            value={getDisplayValue('outlook_allowed_sender_domains')}
            onChange={(v) => handleFieldChange('outlook_allowed_sender_domains', v)}
            placeholder="alphasights.com, guidepoint.com, glg.it"
          />
          <CredentialInput
            label="Network Keywords (Optional)"
            description="Comma-separated keywords to detect expert networks (e.g., AlphaSights, Guidepoint, GLG)"
            value={getDisplayValue('outlook_network_keywords')}
            onChange={(v) => handleFieldChange('outlook_network_keywords', v)}
            placeholder="AlphaSights, Guidepoint, GLG"
          />

          {/* Connection Status */}
          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Connection Status</div>
                {isLoadingOutlook ? (
                  <div className="text-sm text-muted-foreground">Loading...</div>
                ) : outlookStatus?.connected ? (
                  <div className="text-sm text-green-600 flex items-center gap-1">
                    <Check className="w-4 h-4" />
                    Connected as {outlookStatus.userEmail}
                    {outlookStatus.lastTestAt && (
                      <span className="text-muted-foreground ml-2">
                        (tested {new Date(outlookStatus.lastTestAt).toLocaleString()})
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Not connected</div>
                )}
              </div>
              <div className="flex gap-2">
                {outlookStatus?.connected ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => outlookTestMutation.mutate()}
                      disabled={outlookTestMutation.isPending}
                    >
                      {outlookTestMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <RefreshCw className="w-4 h-4 mr-1" />
                          Test
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => outlookDisconnectMutation.mutate()}
                      disabled={outlookDisconnectMutation.isPending}
                    >
                      {outlookDisconnectMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Unlink className="w-4 h-4 mr-1" />
                          Disconnect
                        </>
                      )}
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleConnectOutlook}
                    disabled={!getDisplayValue('outlook_client_id') || !getDisplayValue('outlook_client_secret')}
                  >
                    <Link2 className="w-4 h-4 mr-1" />
                    Connect Outlook
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Outlook Message */}
          {outlookMessage && (
            <div
              className={cn(
                'p-3 rounded-md text-sm',
                outlookMessage.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              )}
            >
              {outlookMessage.text}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <Button
          onClick={handleSave}
          disabled={!hasChanges || saveMutation.isPending}
          className="flex-1"
        >
          {saveMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            'Save Settings'
          )}
        </Button>
        <Button
          variant="outline"
          onClick={handleTest}
          disabled={testMutation.isPending}
        >
          {testMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Test Connections
            </>
          )}
        </Button>
      </div>

      {saveMutation.isSuccess && (
        <div className="p-3 bg-green-50 text-green-700 rounded-md text-sm">
          Settings saved successfully!
        </div>
      )}

      {saveMutation.isError && (
        <div className="p-3 bg-red-50 text-red-700 rounded-md text-sm">
          Failed to save settings. Please try again.
        </div>
      )}
    </div>
  )
}
