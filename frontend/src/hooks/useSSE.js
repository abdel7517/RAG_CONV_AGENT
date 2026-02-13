import { useEffect, useRef, useCallback } from 'react'
import { API_URL } from '@/config'

export function useSSE(email, onMessage, onError) {
  const eventSourceRef = useRef(null)

  const connect = useCallback(() => {
    if (!email) return

    const url = `${API_URL}/api/stream/${encodeURIComponent(email)}`
    const eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        console.error('Erreur parsing SSE:', e)
      }
    }

    eventSource.onerror = (error) => {
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
