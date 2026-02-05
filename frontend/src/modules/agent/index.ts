import { Bot } from 'lucide-react'
import { AgentPage } from './AgentPage'
import type { WorkflowModule } from '../module-registry'

export const AgentModule: WorkflowModule = {
  id: 'agent',
  name: 'AI Agent',
  description: 'Chat with AI to analyze documents and perform tasks',
  icon: Bot,
  path: '/agent',
  component: AgentPage,
}
