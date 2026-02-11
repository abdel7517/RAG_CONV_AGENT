import { useEffect, useRef, useCallback } from 'react'

/**
 * Hook pour suivre la progression du traitement de documents via SSE.
 *
 * Utilise l'endpoint GET /api/documents/progress/{documentId} qui envoie
 * des named events "progress" avec { document_id, step, progress, message, done }.
 *
 * Supporte le suivi de plusieurs documents simultanément.
 */
export function useDocumentProgress() {
  const sourcesRef = useRef({})

  const track = useCallback((documentId, { onProgress, onDone, onError }) => {
    // Fermer une connexion existante pour ce document
    if (sourcesRef.current[documentId]) {
      sourcesRef.current[documentId].close()
    }

    const url = `/api/documents/progress/${documentId}`
    const es = new EventSource(url)

    // Le backend envoie des named events "progress" (pas des events generiques "message")
    es.addEventListener('progress', (event) => {
      try {
        const data = JSON.parse(event.data)
        onProgress?.(data)

        if (data.done) {
          es.close()
          delete sourcesRef.current[documentId]
          onDone?.(data)
        }
      } catch (e) {
        console.error('Erreur parsing SSE progress:', e)
      }
    })

    es.onerror = () => {
      es.close()
      delete sourcesRef.current[documentId]
      onError?.(documentId)
    }

    sourcesRef.current[documentId] = es
  }, [])

  const untrack = useCallback((documentId) => {
    if (sourcesRef.current[documentId]) {
      sourcesRef.current[documentId].close()
      delete sourcesRef.current[documentId]
    }
  }, [])

  // Cleanup toutes les connexions a l'unmount
  useEffect(() => {
    return () => {
      Object.values(sourcesRef.current).forEach((es) => es.close())
      sourcesRef.current = {}
    }
  }, [])

  return { track, untrack }
}
