import { useCallback, useEffect, useState } from 'react'
import EvaluationPanel from '../components/EvaluationPanel.jsx'
import FileUploader from '../components/FileUploader.jsx'
import LengthSelector from '../components/LengthSelector.jsx'
import ModeSelector from '../components/ModeSelector.jsx'
import SummaryDisplay from '../components/SummaryDisplay.jsx'
import {
  checkHealth,
  evaluateDocument,
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

  // Evaluation state
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [evalMetrics, setEvalMetrics] = useState(null)

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
    try {
      const res = await uploadDocument(file)
      setUploadResult(res)
      setPageState('uploaded')
    } catch (err) {
      setErrorMessage(err.message)
      setPageState('error')
    }
  }

  const handleSummarize = async () => {
    if (!uploadResult) return
    setPageState('processing')
    setErrorMessage(null)
    try {
      const res = await summarizeDocument({
        document_id: uploadResult.document_id,
        mode,
        length,
      })
      setSummaryResult(res)
      setPageState('completed')
    } catch (err) {
      setErrorMessage(err.message)
      setPageState('error')
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
          <h3 className="text-sm font-semibold text-ink">Upload Document</h3>
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
              <button
                type="button"
                onClick={handleReset}
                className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
              >
                Upload New File
              </button>
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

            <div className="pt-2">
              <button
                type="button"
                onClick={handleSummarize}
                disabled={pageState === 'processing'}
                className="flex items-center justify-center gap-2 rounded-lg bg-accent px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-accent-strong disabled:opacity-60"
              >
                {pageState === 'processing' ? (
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
                    Generating Summary…
                  </>
                ) : (
                  'Generate Summary'
                )}
              </button>
            </div>
          </section>

          {/* Summary Display Panel */}
          {summaryResult && (
            <SummaryDisplay
              summary={summaryResult.summary}
              mode={summaryResult.mode}
              length={summaryResult.length}
              filename={uploadResult.filename}
            />
          )}

          {/* Evaluation Panel */}
          {summaryResult && (
            <EvaluationPanel
              onEvaluate={handleEvaluate}
              metrics={evalMetrics}
              isEvaluating={isEvaluating}
            />
          )}
        </>
      )}
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
