import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Upload, Trash2, FileText, ArrowLeft, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
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
import { useDocumentProgress } from '@/hooks/useDocumentProgress'
import { API_URL, MAX_PAGES_PER_COMPANY } from '@/config'

const COMPANY_ID = 'techstore_123'

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function DocumentsPage() {
  const [documents, setDocuments] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [progressMap, setProgressMap] = useState({})

  const { track, untrack } = useDocumentProgress()
  const trackedRef = useRef(new Set())

  const startTracking = useCallback((documentId) => {
    if (trackedRef.current.has(documentId)) return
    trackedRef.current.add(documentId)

    track(documentId, {
      onProgress: (data) => {
        setProgressMap((prev) => ({ ...prev, [data.document_id]: data }))
      },
      onDone: (data) => {
        trackedRef.current.delete(data.document_id)
        setProgressMap((prev) => {
          const next = { ...prev }
          delete next[data.document_id]
          return next
        })
        fetchDocuments()
      },
      onError: (docId) => {
        trackedRef.current.delete(docId)
        setProgressMap((prev) => {
          const next = { ...prev }
          delete next[docId]
          return next
        })
        fetchDocuments()
      },
    })
  }, [track])

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/documents?company_id=${COMPANY_ID}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setDocuments(data.documents)
    } catch {
      setDocuments([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // Tracker les documents en cours au chargement initial ou apres refresh
  useEffect(() => {
    documents
      .filter((d) => d.status === 'queued' || d.status === 'vectorizing')
      .forEach((doc) => startTracking(doc.document_id))
  }, [documents, startTracking])

  const handleUpload = async (e) => {
    e.preventDefault()
    const fileInput = e.target.querySelector('input[type="file"]')
    const file = fileInput?.files?.[0]
    if (!file) return

    setIsUploading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_URL}/api/documents/upload?company_id=${COMPANY_ID}`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || "Erreur lors de l'upload")
      }

      const uploaded = await res.json()
      fileInput.value = ''
      await fetchDocuments()

      // Lancer le tracking SSE pour ce document
      startTracking(uploaded.document_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      // Arreter le tracking si en cours
      untrack(deleteTarget.document_id)
      trackedRef.current.delete(deleteTarget.document_id)
      setProgressMap((prev) => {
        const next = { ...prev }
        delete next[deleteTarget.document_id]
        return next
      })

      const res = await fetch(
        `${API_URL}/api/documents/${deleteTarget.document_id}?company_id=${COMPANY_ID}`,
        { method: 'DELETE' }
      )
      if (!res.ok) throw new Error('Erreur lors de la suppression')
      setDeleteTarget(null)
      await fetchDocuments()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Retour
              </Button>
            </Link>
            <Separator orientation="vertical" className="h-6" />
            <h1 className="text-lg font-semibold">Gestion des Documents</h1>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Upload Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Uploader un document PDF
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="flex gap-4 items-end">
              <div className="flex-1">
                <Input
                  type="file"
                  accept=".pdf,application/pdf"
                  required
                  disabled={isUploading}
                />
              </div>
              <Button type="submit" disabled={isUploading}>
                {isUploading ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                {isUploading ? 'Upload en cours...' : 'Uploader'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Error display */}
        {error && (
          <div className="mb-4 p-3 bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        {/* Documents List */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Documents
              </span>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{documents.length} fichier(s)</Badge>
                <Badge variant="outline">
                  {documents.reduce((sum, d) => sum + (d.num_pages || 0), 0)} / {MAX_PAGES_PER_COMPANY} pages
                </Badge>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Chargement...
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Aucun document. Uploadez votre premier PDF ci-dessus.
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => {
                  const prog = progressMap[doc.document_id]
                  return (
                    <div
                      key={doc.document_id}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <FileText className="h-8 w-8 text-red-500 flex-shrink-0" />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium truncate">{doc.filename}</p>
                            <Badge variant={doc.status === 'completed' ? 'default' : doc.status === 'failed' ? 'destructive' : 'secondary'} className="text-xs flex-shrink-0">
                              {prog
                                ? `${prog.progress}%`
                                : doc.status === 'completed' ? 'Vectorise' : doc.status === 'failed' ? 'Erreur' : doc.status === 'queued' ? 'En attente' : 'En cours...'}
                            </Badge>
                          </div>
                          {prog ? (
                            <div className="mt-1.5 space-y-1">
                              <Progress value={prog.progress} className="h-2" />
                              <p className="text-xs text-muted-foreground">{prog.message}</p>
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              {formatFileSize(doc.size_bytes)}
                              {doc.num_pages > 0 && <> &middot; {doc.num_pages} page(s)</>}
                              {doc.uploaded_at && (
                                <> &middot; {new Date(doc.uploaded_at).toLocaleDateString('fr-FR')}</>
                              )}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteTarget(doc)}
                          title="Supprimer"
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce document ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le fichier &quot;{deleteTarget?.filename}&quot; sera definitivement supprime.
              Cette action est irreversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default DocumentsPage
