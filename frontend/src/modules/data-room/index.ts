import { Database } from 'lucide-react'
import { DataRoomPage } from './DataRoomPage'
import type { WorkflowModule } from '../module-registry'

export const DataRoomModule: WorkflowModule = {
  id: 'data-room',
  name: 'Data Room',
  description: 'Chat with your documents using AI',
  icon: Database,
  path: '/data-room',
  component: DataRoomPage,
}
