import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Send, Loader2, Trash2 } from 'lucide-react'
import { dataRoomApi } from '@/services/api'
import { useChatStore } from '@/stores/chatStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble } from './MessageBubble'

export function ChatInterface() {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const { 
    messages, 
    isLoading, 
    addMessage, 
    setLoading, 
    setSelectedSources,
    clearMessages 
  } = useChatStore()

  const chatMutation = useMutation({
    mutationFn: (message: string) => dataRoomApi.chat(message),
    onMutate: () => {
      setLoading(true)
    },
    onSuccess: (data) => {
      addMessage({
        role: 'assistant',
        content: data.response,
        sources: data.sources,
      })
      setLoading(false)
    },
    onError: (error) => {
      addMessage({
        role: 'assistant',
        content: `Error: ${error.message}`,
      })
      setLoading(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    addMessage({ role: 'user', content: input })
    chatMutation.mutate(input)
    setInput('')
  }

  const handleSourceClick = (sources: typeof messages[0]['sources']) => {
    if (sources) {
      setSelectedSources(sources)
    }
  }

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          <h2 className="font-semibold text-lg">Chat with Documents</h2>
          <p className="text-sm text-muted-foreground">
            Ask questions about your ingested documents
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearMessages}
          disabled={messages.length === 0}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Clear
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 px-6" ref={scrollRef}>
        <div className="py-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                Start a conversation by asking a question about your documents.
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onSourceClick={() => handleSourceClick(message.sources)}
              />
            ))
          )}
          
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}
