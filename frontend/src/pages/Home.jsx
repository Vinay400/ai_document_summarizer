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

export default function Home({
  isHistoryOpen: externalHistoryOpen,
  setIsHistoryOpen: externalSetHistoryOpen,
  backendState: externalBackendState,
  setBackendState: externalSetBackendState,
}) {
  // Page state machine: 'idle' | 'uploading' | 'uploaded' | 'processing' | 'completed' | 'error'
  const [pageState, setPageState] = useState('idle')

  // Backend connection status (supports external or internal state)
  const [internalBackendState, setInternalBackendState] = useState('checking')
  const backendState = externalBackendState !== undefined ? externalBackendState : internalBackendState
  const setBackendState = externalSetBackendState || setInternalBackendState

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

  // SQLite History State (supports external or internal state)
  const [internalHistoryOpen, setInternalHistoryOpen] = useState(false)
  const isHistoryOpen = externalHistoryOpen !== undefined ? externalHistoryOpen : internalHistoryOpen
  const setIsHistoryOpen = externalSetHistoryOpen || setInternalHistoryOpen

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
  }, [setBackendState])

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
      {/* Hero Header Section */}
      <section className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-7 sm:p-9 shadow-xs">
        <div className="absolute top-0 right-0 -mt-6 -mr-6 h-48 w-48 rounded-full bg-gradient-to-br from-indigo-500/10 to-purple-500/10 blur-2xl pointer-events-none" />
        <div className="relative">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200/60 bg-indigo-50/70 px-3 py-1 text-xs font-semibold text-indigo-700 mb-3.5">
            <span className="flex h-1.5 w-1.5 rounded-full bg-indigo-600 animate-pulse" />
            MCA Minor Project &middot; Intelligent Document Intelligence
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
            Automated Summarization &amp; Grounded Q&amp;A
          </h2>
          <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-slate-600">
            Synthesize research papers, contracts, and long-form publications using three AI paradigms:
            factually grounded <span className="font-semibold text-slate-800">TextRank Extractive</span>, fluent <span className="font-semibold text-slate-800">BART Abstractive</span>, or a balanced <span className="font-semibold text-slate-800">Hybrid Pipeline</span> with live RAG Q&amp;A and quality analytics.
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { title: 'Extractive Mode', detail: 'Zero-hallucination TextRank', icon: '🛡️' },
              { title: 'Abstractive Mode', detail: 'BART Map-Reduce Engine', icon: '🧠' },
              { title: 'Hybrid Pipeline', detail: 'TextRank filter + BART', icon: '⚡' },
              { title: 'Interactive RAG', detail: 'Instant Document Q&A', icon: '💬' },
            ].map(({ title, detail, icon }) => (
              <div key={title} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 shadow-2xs">
                <div className="flex items-center gap-2">
                  <span className="text-base">{icon}</span>
                  <span className="text-xs font-bold text-slate-900">{title}</span>
                </div>
                <p className="mt-1 text-[11px] text-slate-500">{detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Backend connection probe banner (shown when not online) */}
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
          className="rounded-xl border border-rose-200 bg-rose-50 p-5 shadow-xs"
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-base">⚠️</span>
            <div className="flex-1">
              <h3 className="text-sm font-bold text-rose-800">System Notice</h3>
              <p className="mt-1 text-xs text-rose-700">{errorMessage}</p>
              <button
                type="button"
                onClick={() => setErrorMessage(null)}
                className="mt-3 rounded-lg border border-rose-300 bg-white px-3 py-1 text-xs font-semibold text-rose-800 hover:bg-rose-50 transition"
              >
                Dismiss
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Upload Document Section */}
      {pageState === 'idle' || pageState === 'uploading' ? (
        <section className="space-y-4 rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900">Upload Source Document</h3>
            <button
              type="button"
              onClick={() => setIsHistoryOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:border-indigo-300 hover:text-indigo-600 active:scale-95"
            >
              <span>📁</span> Saved Documents History
            </button>
          </div>
          <FileUploader onUpload={handleUpload} isUploading={pageState === 'uploading'} />
        </section>
      ) : null}

      {uploadResult && (
        <>
          {/* Document Intelligence Dossier */}
          <section className="space-y-5 rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-xl text-indigo-600">
                  {uploadResult.file_type === 'pdf' ? '📕' : uploadResult.file_type === 'docx' ? '📘' : '📄'}
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">{uploadResult.filename}</h3>
                  <p className="text-xs text-slate-500">
                    ID: <span className="font-mono text-slate-600">{uploadResult.document_id}</span> &middot;{' '}
                    <span className="uppercase font-semibold text-indigo-600">{uploadResult.file_type}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsHistoryOpen(true)}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:bg-slate-50 hover:text-slate-900 active:scale-95"
                >
                  <span>📁</span> History
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:bg-slate-50 hover:text-slate-900 active:scale-95"
                >
                  Upload New
                </button>
              </div>
            </div>

            {/* 4 Stat Cards */}
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 shadow-2xs">
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Words / Characters
                </dt>
                <dd className="mt-1 text-sm font-extrabold text-slate-900">
                  {uploadResult.word_count.toLocaleString()} <span className="text-xs font-normal text-slate-500">words</span>
                </dd>
                <p className="text-[11px] text-slate-400">
                  {uploadResult.character_count.toLocaleString()} chars
                </p>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 shadow-2xs">
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Pages Count
                </dt>
                <dd className="mt-1 text-sm font-extrabold text-slate-900">
                  {uploadResult.page_count ?? 'N/A'} <span className="text-xs font-normal text-slate-500">pages</span>
                </dd>
                <p className="text-[11px] text-slate-400">
                  ~{Math.ceil(uploadResult.word_count / 220)} min read time
                </p>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 shadow-2xs">
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Context Chunks
                </dt>
                <dd className="mt-1 text-sm font-extrabold text-slate-900">
                  {uploadResult.chunk_count} <span className="text-xs font-normal text-slate-500">chunk(s)</span>
                </dd>
                <p className="text-[11px] text-slate-400">
                  Sentence-aware seams
                </p>
              </div>

              <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5 shadow-2xs">
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Extraction Pipeline
                </dt>
                <dd className="mt-1 text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
                  <span className="capitalize">{uploadResult.extraction_method}</span>
                  {uploadResult.ocr_used && (
                    <span className="rounded bg-amber-100 px-1.5 py-0.2 text-[10px] font-bold text-amber-800">
                      OCR
                    </span>
                  )}
                </dd>
                <p className="text-[11px] text-slate-400">
                  {uploadResult.ocr_used ? 'Tesseract Scanned OCR' : 'Digital native layer'}
                </p>
              </div>
            </dl>

            {/* Warnings */}
            {uploadResult.warnings && uploadResult.warnings.length > 0 && (
              <div className="space-y-1 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-800">
                <p className="font-bold">Extraction Warnings:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {uploadResult.warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Document Preview */}
            {uploadResult.preview && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Document Text Preview
                  </label>
                  <span className="text-[11px] text-slate-400">First ~280 characters</span>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 font-mono text-xs leading-relaxed text-slate-600">
                  {uploadResult.preview}&hellip;
                </div>
              </div>
            )}

            {/* Cleaning details */}
            {uploadResult.cleaning && (
              <p className="text-[11px] text-slate-400">
                Preprocessing stats: {uploadResult.cleaning.removed_line_count} header/footer lines removed,{' '}
                {uploadResult.cleaning.hyphenation_joins} hyphenation breaks joined.
              </p>
            )}
          </section>

          {/* Configuration & Summarization Controls */}
          <section className="space-y-6 rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs">
            <h3 className="border-b border-slate-100 pb-3 text-base font-bold text-slate-900">
              Summarization Controls &amp; Model Dispatch
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
                className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 px-6 py-3 text-sm font-bold text-white shadow-md shadow-indigo-600/20 transition hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-60 active:scale-95"
              >
                {pageState === 'processing' && !isComparing ? (
                  <>
                    <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
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
                className="flex items-center justify-center gap-2 rounded-xl border border-purple-200 bg-purple-50/70 px-6 py-3 text-sm font-bold text-purple-700 shadow-2xs transition hover:bg-purple-100 hover:border-purple-300 disabled:opacity-60 active:scale-95"
              >
                {pageState === 'processing' && isComparing ? (
                  <>
                    <svg className="h-4 w-4 animate-spin text-purple-700" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
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
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/90 bg-white px-5 py-3.5 shadow-xs">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Active Results View
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setViewMode('single')}
                  disabled={!summaryResult}
                  className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
                    viewMode === 'single'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:text-slate-900 disabled:opacity-40'
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
                  className={`flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-bold transition ${
                    viewMode === 'compare'
                      ? 'bg-purple-600 text-white shadow-xs'
                      : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                  }`}
                >
                  <span>⚡ 3-Way Comparison Matrix</span>
                  {!comparisonResult && (
                    <span className="rounded bg-purple-200/60 px-1.5 py-0.5 text-[10px] uppercase font-bold text-purple-800">
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
      <section className="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50/70 p-5 shadow-xs">
        <span className="h-3 w-3 animate-ping rounded-full bg-amber-500" aria-hidden="true" />
        <p className="text-xs font-semibold text-amber-800">Probing backend service connectivity&hellip;</p>
      </section>
    )
  }

  if (state === 'offline') {
    return (
      <section
        role="alert"
        className="rounded-2xl border border-rose-200 bg-rose-50/90 p-6 shadow-xs"
      >
        <div className="flex items-start gap-3.5">
          <span className="text-lg">🛑</span>
          <div className="flex-1">
            <h3 className="text-sm font-bold text-rose-800">FastAPI Backend Server Offline</h3>
            <p className="mt-1 text-xs text-rose-700">{error}</p>
            <div className="mt-3 rounded-xl bg-white p-3 font-mono text-xs text-slate-700 border border-rose-200">
              cd backend &amp;&amp; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="mt-3.5 rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-rose-700 transition"
            >
              Retry Connection
            </button>
          </div>
        </div>
      </section>
    )
  }

  return null
}
