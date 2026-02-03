import type { LucideIcon } from 'lucide-react'
import { DataRoomModule } from './data-room'

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
  // Add ExpertNetworkModule here when ready
]
