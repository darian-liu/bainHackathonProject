import { Settings } from 'lucide-react'
import { SettingsPage } from './SettingsPage'
import type { WorkflowModule } from '../module-registry'

export const SettingsModule: WorkflowModule = {
  id: 'settings',
  name: 'Settings',
  description: 'Configure API credentials and preferences',
  icon: Settings,
  path: '/settings',
  component: SettingsPage,
}
