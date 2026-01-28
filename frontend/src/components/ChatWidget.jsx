import React, { useState, useRef, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, BotMessageSquare, Minus, User, Bot } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Skeleton } from '@/components/ui/skeleton'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useSSE } from '@/hooks/useSSE'
import { cn } from '@/lib/utils'

function ChatMessage({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={cn(
      "mb-3 flex gap-2",
      isUser ? "flex-row-reverse" : "flex-row"
    )}>
      <Avatar className="h-8 w-8 flex-shrink-0">
        <AvatarFallback className={cn(
          isUser ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground"
        )}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div className={cn(
        "max-w-[75%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap",
        isUser
          ? "bg-primary text-primary-foreground rounded-tr-none"
          : "bg-muted text-foreground rounded-tl-none"
      )}>
        {content}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 mb-3">
      <Avatar className="h-8 w-8">
        <AvatarFallback className="bg-primary text-primary-foreground">
          <Bot className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>
      <div className="space-y-2 pt-1">
        <Skeleton className="h-4 w-[200px]" />
        <Skeleton className="h-4 w-[150px]" />
      </div>
    </div>
  )
}

export function ChatWidget({ defaultEmail = '', companyId }) {
  // Validation: companyId est obligatoire
  if (!companyId) {
    console.error('[ChatWidget] Erreur: companyId est requis', { companyId })
    return null
  }

  const [isOpen, setIsOpen] = useState(false)
  const [email, setEmail] = useState(defaultEmail)
  const [isConnected, setIsConnected] = useState(!!defaultEmail)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const [showCloseAlert, setShowCloseAlert] = useState(false)
  const messagesEndRef = useRef(null)
  const responseBufferRef = useRef('')

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse])

  const handleSSEMessage = useCallback((data) => {
    if (data.done) {
      const finalContent = responseBufferRef.current + (data.chunk || '')
      if (finalContent) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: finalContent
        }])
      }
      responseBufferRef.current = ''
      setCurrentResponse('')
      setIsLoading(false)
    } else {
      responseBufferRef.current += data.chunk
      setCurrentResponse(responseBufferRef.current)
    }
  }, [])

  const { connect, disconnect } = useSSE(email, handleSSEMessage)

  const handleConnect = (e) => {
    e.preventDefault()
    if (email.trim()) {
      setIsConnected(true)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)
    setCurrentResponse('')
    responseBufferRef.current = ''

    connect()

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_id: companyId,  // Multi-tenant: ID entreprise
          email,
          message: userMessage
        })
      })

      if (!response.ok) {
        throw new Error('Erreur lors de l\'envoi du message')
      }
    } catch (error) {
      console.error('Erreur:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Erreur de connexion au serveur.'
      }])
      setIsLoading(false)
      disconnect()
    }
  }

  const handleCloseChat = () => {
    setShowCloseAlert(false)
    setIsOpen(false)
    setIsConnected(false)
    setMessages([])
    setEmail('')
    setInput('')
    setCurrentResponse('')
    responseBufferRef.current = ''
    disconnect()
  }

  const handleMinimize = () => {
    setIsOpen(false)
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Alerte de confirmation de fermeture */}
      <AlertDialog open={showCloseAlert} onOpenChange={setShowCloseAlert}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fermer la conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              Si vous fermez le chat, la conversation en cours sera perdue.
              Etes-vous sur de vouloir continuer?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleCloseChat}>
              Fermer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Panel de chat */}
      {isOpen && (
        <Card className="w-[380px] h-[500px] mb-4 flex flex-col shadow-xl animate-in slide-in-from-bottom-5 duration-1000 ease-out">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 border-b">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <span className="text-xl"><BotMessageSquare /></span> Assistant
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleMinimize}
              className="h-8 w-8"
              title="Reduire"
            >
              <Minus className="h-4 w-4" />
            </Button>
          </CardHeader>

          {!isConnected ? (
            <CardContent className="flex-1 flex items-center justify-center">
              <form onSubmit={handleConnect} className="w-full space-y-4 px-4">
                <div className="text-center space-y-2">
                  <h3 className="font-medium">Bienvenue!</h3>
                  <p className="text-sm text-muted-foreground">
                    Entrez votre email pour commencer
                  </p>
                </div>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="votre@email.com"
                  required
                />
                <Button type="submit" className="w-full">
                  Commencer
                </Button>
              </form>
            </CardContent>
          ) : (
            <>
              <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-[350px] p-4">
                  {messages.length === 0 && (
                    <div className="text-center text-muted-foreground text-sm py-8">
                      Posez-moi une question!
                    </div>
                  )}

                  {messages.map((msg, i) => (
                    <ChatMessage key={i} role={msg.role} content={msg.content} />
                  ))}

                  {isLoading && currentResponse && (
                    <ChatMessage role="assistant" content={currentResponse} />
                  )}

                  {isLoading && !currentResponse && <TypingIndicator />}

                  <div ref={messagesEndRef} />
                </ScrollArea>
              </CardContent>

              <CardFooter className="border-t p-3">
                <form onSubmit={handleSendMessage} className="flex w-full gap-2">
                  <Input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Votre message..."
                    disabled={isLoading}
                    className="flex-1"
                  />
                  <Button
                    type="submit"
                    size="icon"
                    disabled={isLoading || !input.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </CardFooter>
            </>
          )}
        </Card>
      )}

      {/* Bouton flottant */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => isOpen ? setShowCloseAlert(true) : setIsOpen(true)}
              size="icon"
              className={cn(
                "h-14 w-14 rounded-full shadow-lg",
                "transition-all duration-[8000ms] ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                "hover:scale-110 hover:shadow-xl",
                isOpen && "bg-destructive hover:bg-destructive/90 rotate-180"
              )}
            >
              {isOpen ? (
                <X className="h-6 w-6 transition-transform duration-[8000ms]" />
              ) : (
                <MessageCircle className="h-6 w-6 transition-transform duration-[8000ms]" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">
            <p>{isOpen ? "Fermer la conversation" : "Discuter avec l'assistant"}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}

export default ChatWidget
