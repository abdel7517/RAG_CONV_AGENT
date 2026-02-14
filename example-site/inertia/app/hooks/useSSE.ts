import { useEffect, useRef, useCallback } from 'react'
import { API_URL } from '~/app/config'

interface SSEData {
  chunk?: string
  done?: boolean
  [key: string]: unknown
}

type OnMessageCallback = (data: SSEData) => void
type OnErrorCallback = (error: Event) => void

interface UseSSEReturn {
  connect: () => void
  disconnect: () => void
}

export function useSSE(
  email: string | null,
  onMessage: OnMessageCallback,
  onError?: OnErrorCallback
): UseSSEReturn {
  const eventSourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (!email) return

    const url = `${API_URL}/api/stream/${encodeURIComponent(email)}`
    const eventSource = new EventSource(url)

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const data: SSEData = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('Erreur parsing SSE:', e)
      }
    }

    eventSource.onerror = (error: Event) => {
      console.error('Erreur SSE:', error)
      if (onError) onError(error)
      eventSource.close()
    }

    eventSourceRef.current = eventSource
  }, [email, onMessage, onError])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return { connect, disconnect }
}
