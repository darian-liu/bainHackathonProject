import type { LucideIcon } from 'lucide-react'
import { DataRoomModule } from './data-room'
import { SettingsModule } from './settings'
import { ExpertNetworksModule } from './expert-networks'
import { AgentModule } from './agent'

export interface WorkflowModule {
  id: string
  name: string
  description: string
  icon: LucideIcon
  path: string
  component: React.ComponentType
}

export const modules: WorkflowModule[] = [
  DataRoomModule,
  ExpertNetworksModule,
  AgentModule,
  SettingsModule,
]
