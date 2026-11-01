import { useState, useEffect, useCallback } from 'react'
import { fetchHistory, deleteHistoryItem } from '../services/api.js'

export default function HistoryDrawer({ isOpen, onClose, onSelectDocument }) {
  const [historyItems, setHistoryItems] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadHistory = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchHistory()
      setHistoryItems(data.documents || [])
    } catch (err) {
      setError(err.message || 'Failed to load history.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      loadHistory()
    }
  }, [isOpen, loadHistory])

  const handleDelete = async (e, docId) => {
    e.stopPropagation()
    try {
      await deleteHistoryItem(docId)
      setHistoryItems((prev) => prev.filter((d) => d.document_id !== docId))
    } catch (err) {
      alert(`Could not delete item: ${err.message}`)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
      <div className="flex h-full w-full max-w-md flex-col border-l border-edge bg-surface p-6 shadow-2xl transition">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-edge pb-4">
          <div className="flex items-center gap-2">
            <span className="text-lg">📁</span>
            <div>
              <h2 className="text-base font-semibold text-ink">Document History</h2>
              <p className="text-xs text-ink-muted">Persistent SQLite Document Store</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadHistory}
              disabled={isLoading}
              className="rounded-md border border-edge p-1.5 text-xs text-ink hover:bg-surface-sunken"
              title="Refresh history"
            >
              🔄
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-edge p-1.5 text-xs font-bold text-ink hover:bg-surface-sunken"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto py-4">
          {isLoading && (
            <div className="py-12 text-center text-xs text-ink-muted">
              Loading saved documents…
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-600 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          {!isLoading && historyItems.length === 0 && !error && (
            <div className="py-12 text-center text-xs text-ink-muted">
              No saved documents yet. Upload a document to see it saved here automatically.
            </div>
          )}

          <div className="space-y-3">
            {historyItems.map((item) => (
              <div
                key={item.document_id}
                onClick={() => {
                  onSelectDocument(item)
                  onClose()
                }}
                className="group relative cursor-pointer rounded-lg border border-edge bg-surface p-3.5 transition hover:border-accent hover:bg-surface-sunken"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="truncate text-xs font-semibold text-ink group-hover:text-accent">
                      {item.filename}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
                      <span className="rounded bg-surface-sunken px-1.5 py-0.5 font-mono uppercase">
                        {item.file_type}
                      </span>
                      <span>{item.word_count.toLocaleString()} words</span>
                      {item.ocr_used && (
                        <span className="text-amber-600 dark:text-amber-400 font-medium">
                          OCR
                        </span>
                      )}
                      <span>&middot;</span>
                      <span>{item.summary_count} summaries</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, item.document_id)}
                    className="opacity-0 group-hover:opacity-100 rounded p-1 text-xs text-ink-subtle hover:text-red-500 transition"
                    title="Delete document"
                  >
                    🗑️
                  </button>
                </div>

                {item.preview && (
                  <p className="mt-2 line-clamp-2 text-[11px] text-ink-subtle italic">
                    &ldquo;{item.preview}&rdquo;
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-edge pt-4 text-center text-[11px] text-ink-muted">
          All documents and summaries are stored persistently in SQLite.
        </div>
      </div>
    </div>
  )
}

