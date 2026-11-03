import { useState, useEffect, useCallback } from 'react'
import { fetchHistory, deleteHistoryItem } from '../services/api.js'

export default function HistoryDrawer({ isOpen, onClose, onSelectDocument }) {
  const [historyItems, setHistoryItems] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
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
    if (!window.confirm('Delete this document and its generated summaries from history?')) {
      return
    }
    try {
      await deleteHistoryItem(docId)
      setHistoryItems((prev) => prev.filter((d) => d.document_id !== docId))
    } catch (err) {
      alert(`Could not delete item: ${err.message}`)
    }
  }

  const filteredItems = historyItems.filter((item) => {
    if (!searchTerm.trim()) return true
    const term = searchTerm.toLowerCase()
    return (
      item.filename.toLowerCase().includes(term) ||
      (item.preview && item.preview.toLowerCase().includes(term))
    )
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs transition duration-200">
      <div className="flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white p-6 shadow-2xl transition">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              📁
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">Document History</h2>
              <p className="text-xs text-slate-500">Persistent SQLite Store</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadHistory}
              disabled={isLoading}
              className="rounded-lg border border-slate-200 p-1.5 text-xs text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
              title="Refresh history"
            >
              🔄
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 p-1.5 text-xs font-bold text-slate-500 hover:bg-slate-50 hover:text-slate-800 transition"
              title="Close drawer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Search filter input */}
        <div className="pt-4 pb-2">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search saved documents..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto py-2 space-y-3">
          {isLoading && (
            <div className="py-16 text-center text-xs text-slate-400">
              <span className="inline-block animate-spin mr-2">⏳</span> Loading documents…
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-700">
              {error}
            </div>
          )}

          {!isLoading && filteredItems.length === 0 && !error && (
            <div className="py-16 text-center text-xs text-slate-400 space-y-1">
              <p className="text-2xl">📭</p>
              <p className="font-medium text-slate-600">No documents found</p>
              <p className="text-[11px] text-slate-400">
                {searchTerm ? 'Try a different search term.' : 'Uploaded documents will appear here automatically.'}
              </p>
            </div>
          )}

          {filteredItems.map((item) => (
            <div
              key={item.document_id}
              onClick={() => {
                onSelectDocument(item)
                onClose()
              }}
              className="group relative cursor-pointer rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs transition hover:border-indigo-400 hover:bg-indigo-50/20 hover:shadow-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="truncate text-xs font-bold text-slate-900 group-hover:text-indigo-600">
                    {item.filename}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase text-slate-700">
                      {item.file_type}
                    </span>
                    <span>{item.word_count.toLocaleString()} words</span>
                    {item.ocr_used && (
                      <span className="font-semibold text-amber-600">
                        OCR
                      </span>
                    )}
                    <span>&middot;</span>
                    <span className="text-indigo-600 font-medium">
                      {item.summary_count} {item.summary_count === 1 ? 'summary' : 'summaries'}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => handleDelete(e, item.document_id)}
                  className="rounded p-1 text-xs text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
                  title="Delete from history"
                >
                  🗑️
                </button>
              </div>

              {item.preview && (
                <p className="mt-2 line-clamp-2 text-[11px] text-slate-500 italic bg-slate-50 p-2 rounded-lg">
                  &ldquo;{item.preview}&rdquo;
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 pt-3 text-center text-[11px] text-slate-400">
          All data is persistently stored in SQLite (`uploads/history.db`).
        </div>
      </div>
    </div>
  )
}
