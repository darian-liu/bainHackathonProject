import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Settings, Eye, EyeOff, Loader2, Check, X, RefreshCw } from 'lucide-react'
import { settingsApi, type SettingsData } from '@/services/api'
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
  const [formData, setFormData] = useState<Partial<SettingsData>>({})
  const [hasChanges, setHasChanges] = useState(false)

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

      {/* OpenAI Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>OpenAI Configuration</CardTitle>
          <CardDescription>
            Required for document embeddings and chat functionality
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CredentialInput
            label="OpenAI API Key"
            description="Your OpenAI API key for embeddings and chat"
            value={getDisplayValue('openai_api_key')}
            onChange={(v) => handleFieldChange('openai_api_key', v)}
            placeholder="sk-..."
            isSecret
          />
        </CardContent>
      </Card>

      {/* Microsoft Graph Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Microsoft Graph Configuration</CardTitle>
          <CardDescription>
            Required for SharePoint integration (live mode)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <CredentialInput
            label="Client ID"
            description="Azure AD App Registration Client ID"
            value={getDisplayValue('graph_client_id')}
            onChange={(v) => handleFieldChange('graph_client_id', v)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          />
          <CredentialInput
            label="Client Secret"
            description="Azure AD App Registration Client Secret"
            value={getDisplayValue('graph_client_secret')}
            onChange={(v) => handleFieldChange('graph_client_secret', v)}
            placeholder="Your client secret"
            isSecret
          />
          <CredentialInput
            label="Tenant ID"
            description="Microsoft 365 Tenant ID"
            value={getDisplayValue('graph_tenant_id')}
            onChange={(v) => handleFieldChange('graph_tenant_id', v)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          />
          <CredentialInput
            label="SharePoint Site ID"
            description="The ID of your SharePoint site"
            value={getDisplayValue('sharepoint_site_id')}
            onChange={(v) => handleFieldChange('sharepoint_site_id', v)}
            placeholder="Your SharePoint site ID"
          />
        </CardContent>
      </Card>

      {/* Document Source Mode */}
      <Card>
        <CardHeader>
          <CardTitle>Document Source</CardTitle>
          <CardDescription>
            Choose between local demo files or live SharePoint connection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <button
              onClick={() => handleFieldChange('document_source_mode', 'mock')}
              className={cn(
                'flex-1 p-4 border rounded-lg text-left transition-colors',
                getDisplayValue('document_source_mode') === 'mock'
                  ? 'border-blue-500 bg-blue-50'
                  : 'hover:bg-slate-50'
              )}
            >
              <div className="font-medium">Mock Mode</div>
              <div className="text-sm text-muted-foreground">
                Use local demo-docs folder
              </div>
            </button>
            <button
              onClick={() => handleFieldChange('document_source_mode', 'live')}
              className={cn(
                'flex-1 p-4 border rounded-lg text-left transition-colors',
                getDisplayValue('document_source_mode') === 'live'
                  ? 'border-blue-500 bg-blue-50'
                  : 'hover:bg-slate-50'
              )}
            >
              <div className="font-medium">Live Mode</div>
              <div className="text-sm text-muted-foreground">
                Connect to SharePoint
              </div>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Test Connection Results */}
      {testMutation.data && (
        <Card>
          <CardHeader>
            <CardTitle>Connection Test Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              {testMutation.data.openai ? (
                <Check className="w-5 h-5 text-green-500" />
              ) : (
                <X className="w-5 h-5 text-red-500" />
              )}
              <span>OpenAI API</span>
              {testMutation.data.errors?.openai && (
                <span className="text-sm text-red-500 ml-auto">
                  {testMutation.data.errors.openai}
                </span>
              )}
            </div>
            {testMutation.data.sharepoint !== null && (
              <div className="flex items-center gap-2">
                {testMutation.data.sharepoint ? (
                  <Check className="w-5 h-5 text-green-500" />
                ) : (
                  <X className="w-5 h-5 text-red-500" />
                )}
                <span>SharePoint</span>
                {testMutation.data.errors?.sharepoint && (
                  <span className="text-sm text-red-500 ml-auto">
                    {testMutation.data.errors.sharepoint}
                  </span>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
