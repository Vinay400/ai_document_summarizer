import { useCallback, useEffect, useState } from 'react'
import ComparisonMatrix from '../components/ComparisonMatrix.jsx'
import DocumentChat from '../components/DocumentChat.jsx'
import EvaluationPanel from '../components/EvaluationPanel.jsx'
import FileUploader from '../components/FileUploader.jsx'
import HistoryDrawer from '../components/HistoryDrawer.jsx'
import LengthSelector from '../components/LengthSelector.jsx'
import ModeSelector from '../components/ModeSelector.jsx'
import SummaryDisplay from '../components/SummaryDisplay.jsx'
import {
  checkHealth,
  compareEvaluateDocument,
  compareSummarizeDocument,
  evaluateDocument,
  fetchHistoryDocument,
  summarizeDocument,
  uploadDocument,
} from '../services/api.js'

export default function Home() {
  // Page state machine: 'idle' | 'uploading' | 'uploaded' | 'processing' | 'completed' | 'error'
  const [pageState, setPageState] = useState('idle')

  // Backend connection status
  const [backendState, setBackendState] = useState('checking')
  const [health, setHealth] = useState(null)
  const [backendError, setBackendError] = useState(null)

  // Document & Summarization state
  const [uploadResult, setUploadResult] = useState(null)
  const [mode, setMode] = useState('extractive')
  const [length, setLength] = useState('medium')
  const [summaryResult, setSummaryResult] = useState(null)

  // Comparison state
  const [viewMode, setViewMode] = useState('single') // 'single' | 'compare'
  const [isComparing, setIsComparing] = useState(false)
  const [comparisonResult, setComparisonResult] = useState(null)
  const [comparisonMetrics, setComparisonMetrics] = useState(null)
  const [isComparingEval, setIsComparingEval] = useState(false)

  // Evaluation state
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evalMetrics, setEvalMetrics] = useState(null)

  // SQLite History State
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)

  // Error handling
  const [errorMessage, setErrorMessage] = useState(null)

  const probeBackend = useCallback(async () => {
    setBackendState('checking')
    setBackendError(null)
    try {
      const data = await checkHealth()
      setHealth(data)
      setBackendState('online')
    } catch (err) {
      setBackendError(err.message)
      setHealth(null)
      setBackendState('offline')
    }
  }, [])

  useEffect(() => {
    probeBackend()
  }, [probeBackend])

  const handleUpload = async (file) => {
    setPageState('uploading')
    setErrorMessage(null)
    setSummaryResult(null)
    setEvalMetrics(null)
    setComparisonResult(null)
    setComparisonMetrics(null)
    setViewMode('single')
    try {
      const res = await uploadDocument(file)
      setUploadResult(res)
      setPageState('uploaded')
    } catch (err) {
      setErrorMessage(err.message)
      setPageState('error')
    }
  }

  const handleSelectFromHistory = async (item) => {
    setErrorMessage(null)
    setUploadResult({
      document_id: item.document_id,
      filename: item.filename,
      file_type: item.file_type,
      character_count: item.character_count,
      word_count: item.word_count,
      page_count: item.page_count,
      ocr_used: item.ocr_used,
      extraction_method: item.extraction_method,
      preview: item.preview,
      cleaning: null,
      warnings: [],
    })
    setSummaryResult(null)
    setComparisonResult(null)
    setEvalMetrics(null)
    setComparisonMetrics(null)
    setViewMode('single')
    setPageState('uploaded')

    try {
      const details = await fetchHistoryDocument(item.document_id)
      if (details?.summaries?.length > 0) {
        const latest = details.summaries[0]
        setSummaryResult({
          document_id: latest.document_id,
          mode: latest.mode,
          length: latest.length,
          summary: latest.summary,
          analytics: latest.analytics,
        })
        setMode(latest.mode)
        setLength(latest.length)
        setPageState('completed')
      }
    } catch {
      // Ignored: document metadata is already set
    }
  }

  const handleSummarize = async () => {
    if (!uploadResult) return
    setPageState('processing')
    setIsComparing(false)
    setErrorMessage(null)
    try {
      const res = await summarizeDocument({
        document_id: uploadResult.document_id,
        mode,
        length,
      })
      setSummaryResult(res)
      setViewMode('single')
      setPageState('completed')
    } catch (err) {
      setErrorMessage(err.message)
      setPageState('error')
    }
  }

  const handleCompareAll = async () => {
    if (!uploadResult) return
    setPageState('processing')
    setIsComparing(true)
    setErrorMessage(null)
    try {
      const res = await compareSummarizeDocument({
        document_id: uploadResult.document_id,
        length,
      })
      setComparisonResult(res)
      setViewMode('compare')
      setPageState('completed')
    } catch (err) {
      setErrorMessage(err.message)
      setPageState('error')
    } finally {
      setIsComparing(false)
    }
  }

  const handleCompareEvaluate = async (reference, summaries) => {
    if (!uploadResult) return
    setIsComparingEval(true)
    setErrorMessage(null)
    try {
      const res = await compareEvaluateDocument({
        document_id: uploadResult.document_id,
        reference,
        length,
        summaries,
      })
      setComparisonMetrics(res.modes)
    } catch (err) {
      setErrorMessage(err.message)
    } finally {
      setIsComparingEval(false)
    }
  }

  const handleEvaluate = async (reference) => {
    if (!uploadResult) return
    setIsEvaluating(true)
    try {
      const res = await evaluateDocument({
        document_id: uploadResult.document_id,
        reference,
        mode,
        length,
      })
      setEvalMetrics(res.metrics)
      if (res.summary) {
        setSummaryResult((prev) => ({ ...prev, summary: res.summary }))
      }
    } catch (err) {
      setErrorMessage(err.message)
    } finally {
      setIsEvaluating(false)
    }
  }

  const handleReset = () => {
    setPageState('idle')
    setUploadResult(null)
    setSummaryResult(null)
    setEvalMetrics(null)
    setComparisonResult(null)
    setComparisonMetrics(null)
    setViewMode('single')
    setIsComparing(false)
    setErrorMessage(null)
  }


  return (
    <div className="space-y-6">
      {/* Header section */}
      <section className="rounded-xl border border-edge bg-surface p-6 shadow-sm">
        <h2 className="text-xl font-semibold tracking-tight text-ink">
          AI Document Summarization
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
          An intelligent extractive, abstractive and hybrid summarization platform
          for long-form documents. Upload a PDF, DOCX or TXT file, choose a strategy,
          and evaluate the generated summary with ROUGE and BLEU.
        </p>

        <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { term: 'PDF', detail: 'Text + OCR fallback' },
            { term: 'DOCX', detail: 'Paragraph + table text' },
            { term: 'TXT', detail: 'Encoding-aware read' },
            { term: 'Modes', detail: 'Extractive / Abstractive / Hybrid' },
          ].map(({ term, detail }) => (
            <div key={term} className="rounded-lg bg-surface-sunken p-3">
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                {term}
              </dt>
              <dd className="mt-1 text-xs text-ink-muted">{detail}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Backend connection probe banner */}
      {backendState !== 'online' && (
        <BackendStatus
          state={backendState}
          health={health}
          error={backendError}
          onRetry={probeBackend}
        />
      )}

      {/* Error alert panel */}
      {errorMessage && (
        <section
          role="alert"
          className="rounded-xl border border-danger/30 bg-danger-soft p-6 shadow-sm"
        >
          <div className="flex items-start gap-3">
            <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-danger" aria-hidden="true" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-danger">Error</h3>
              <p className="mt-1 text-sm text-ink-muted">{errorMessage}</p>
              <button
                type="button"
                onClick={() => setErrorMessage(null)}
                className="mt-3 rounded-md border border-edge bg-surface px-3 py-1 text-xs font-medium text-ink hover:border-edge-strong"
              >
                Dismiss
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Main Flow */}
      {pageState === 'idle' || pageState === 'uploading' ? (
        <section className="space-y-4 rounded-xl border border-edge bg-surface p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink">Upload Document</h3>
            <button
              type="button"
              onClick={() => setIsHistoryOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-edge bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-accent hover:text-accent"
            >
              <span>📁</span> Saved Documents History
            </button>
          </div>
          <FileUploader onUpload={handleUpload} isUploading={pageState === 'uploading'} />
        </section>
      ) : null}

      {uploadResult && (
        <>
          {/* Metadata Display Panel */}
          <section className="space-y-4 rounded-xl border border-edge bg-surface p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-edge pb-3">
              <div>
                <h3 className="text-base font-semibold text-ink">{uploadResult.filename}</h3>
                <p className="text-xs text-ink-muted">
                  Document ID: <span className="font-mono text-ink-subtle">{uploadResult.document_id}</span>
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsHistoryOpen(true)}
                  className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
                >
                  📁 History
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
                >
                  Upload New File
                </button>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg bg-surface-sunken p-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                  Words / Chars
                </dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {uploadResult.word_count.toLocaleString()} / {uploadResult.character_count.toLocaleString()}
                </dd>
              </div>
              <div className="rounded-lg bg-surface-sunken p-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                  Chunks
                </dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {uploadResult.chunk_count}
                </dd>
              </div>
              <div className="rounded-lg bg-surface-sunken p-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                  Page Count
                </dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {uploadResult.page_count ?? 'N/A'}
                </dd>
              </div>
              <div className="rounded-lg bg-surface-sunken p-3">
                <dt className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                  Extraction Method
                </dt>
                <dd className="mt-1 text-sm font-medium text-ink">
                  {uploadResult.extraction_method} {uploadResult.ocr_used ? '(OCR)' : ''}
                </dd>
              </div>
            </dl>

            {/* Warnings */}
            {uploadResult.warnings && uploadResult.warnings.length > 0 && (
              <div className="space-y-1 rounded-lg border border-warn/30 bg-warn-soft p-3 text-xs text-warn">
                <p className="font-semibold">Extraction Warnings:</p>
                <ul className="list-disc list-inside">
                  {uploadResult.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Document Preview */}
            {uploadResult.preview && (
              <div className="space-y-1">
                <label className="block text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                  Document Preview
                </label>
                <div className="rounded-lg border border-edge bg-surface-sunken p-3 font-mono text-xs leading-relaxed text-ink-muted">
                  {uploadResult.preview}…
                </div>
              </div>
            )}

            {/* Cleaning summary */}
            {uploadResult.cleaning && (
              <p className="text-xs text-ink-subtle">
                Cleaning details: {uploadResult.cleaning.removed_line_count} line(s) removed,{' '}
                {uploadResult.cleaning.hyphenation_joins} hyphen join(s).
              </p>
            )}
          </section>

          {/* Configuration & Summarize Panel */}
          <section className="space-y-6 rounded-xl border border-edge bg-surface p-6 shadow-sm">
            <h3 className="border-b border-edge pb-2 text-sm font-semibold text-ink">
              Summarization Controls
            </h3>

            <ModeSelector
              value={mode}
              onChange={setMode}
              disabled={pageState === 'processing'}
            />

            <LengthSelector
              value={length}
              onChange={setLength}
              disabled={pageState === 'processing'}
            />

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                type="button"
                onClick={handleSummarize}
                disabled={pageState === 'processing'}
                className="flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-accent-strong disabled:opacity-60"
              >
                {pageState === 'processing' && !isComparing ? (
                  <>
                    <svg
                      className="h-4 w-4 animate-spin text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      />
                    </svg>
                    Generating {mode.charAt(0).toUpperCase() + mode.slice(1)}…
                  </>
                ) : (
                  `Generate ${mode.charAt(0).toUpperCase() + mode.slice(1)} Summary`
                )}
              </button>

              <button
                type="button"
                onClick={handleCompareAll}
                disabled={pageState === 'processing'}
                className="flex items-center justify-center gap-2 rounded-lg border border-purple-300 bg-purple-50/70 px-5 py-2.5 text-sm font-semibold text-purple-700 shadow-sm transition hover:bg-purple-100 hover:border-purple-400 disabled:opacity-60 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300"
              >
                {pageState === 'processing' && isComparing ? (
                  <>
                    <svg
                      className="h-4 w-4 animate-spin text-purple-700 dark:text-purple-300"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      />
                    </svg>
                    Generating All 3 Strategies…
                  </>
                ) : (
                  '⚡ Compare All 3 Modes'
                )}
              </button>
            </div>
          </section>

          {/* View switcher when results exist */}
          {(summaryResult || comparisonResult) && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-edge bg-surface px-5 py-3 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                Active Results View
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setViewMode('single')}
                  disabled={!summaryResult}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                    viewMode === 'single'
                      ? 'bg-accent text-white shadow-sm'
                      : 'bg-surface-sunken text-ink-muted hover:text-ink disabled:opacity-40'
                  }`}
                >
                  Single Strategy View {summaryResult ? `(${summaryResult.mode})` : ''}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!comparisonResult) {
                      handleCompareAll()
                    } else {
                      setViewMode('compare')
                    }
                  }}
                  className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                    viewMode === 'compare'
                      ? 'bg-purple-600 text-white shadow-sm'
                      : 'bg-purple-50 text-purple-700 hover:bg-purple-100 dark:bg-purple-950/30 dark:text-purple-300'
                  }`}
                >
                  <span>⚡ 3-Way Comparison Matrix</span>
                  {!comparisonResult && (
                    <span className="rounded bg-purple-200/60 px-1.5 py-0.5 text-[10px] uppercase font-bold text-purple-800 dark:bg-purple-800 dark:text-purple-200">
                      Run
                    </span>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Conditional Display: Single Strategy vs Comparison Matrix */}
          {viewMode === 'compare' && comparisonResult && (
            <ComparisonMatrix
              comparisonData={comparisonResult}
              filename={uploadResult.filename}
              onEvaluate={handleCompareEvaluate}
              isEvaluating={isComparingEval}
              evaluationMetrics={comparisonMetrics}
            />
          )}

          {viewMode === 'single' && summaryResult && (
            <>
              {/* Summary Display Panel */}
              <SummaryDisplay
                summary={summaryResult.summary}
                mode={summaryResult.mode}
                length={summaryResult.length}
                filename={uploadResult.filename}
                documentId={uploadResult.document_id}
                analytics={summaryResult.analytics}
              />

              {/* Evaluation Panel */}
              <EvaluationPanel
                onEvaluate={handleEvaluate}
                metrics={evalMetrics}
                isEvaluating={isEvaluating}
              />
            </>
          )}

          {/* Interactive Document Q&A (RAG Assistant) */}
          <DocumentChat
            documentId={uploadResult.document_id}
            filename={uploadResult.filename}
          />
        </>
      )}

      {/* Persistent History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectDocument={handleSelectFromHistory}
      />
    </div>
  )
}

function BackendStatus({ state, health, error, onRetry }) {
  if (state === 'checking') {
    return (
      <section className="flex items-center gap-3 rounded-xl border border-edge bg-surface p-6 shadow-sm">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-warn" aria-hidden="true" />
        <p className="text-sm text-ink-muted">Checking backend connection…</p>
      </section>
    )
  }

  if (state === 'offline') {
    return (
      <section
        role="alert"
        className="rounded-xl border border-danger/30 bg-danger-soft p-6 shadow-sm"
      >
        <div className="flex items-start gap-3">
          <span className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-danger" aria-hidden="true" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-danger">Backend unreachable</h3>
            <p className="mt-1 text-sm text-ink-muted">{error}</p>
            <p className="mt-3 rounded-md bg-surface px-3 py-2 font-mono text-xs text-ink-muted">
              cd backend &amp;&amp; .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
            </p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong"
            >
              Retry connection
            </button>
          </div>
        </div>
      </section>
    )
  }

  return null
}
