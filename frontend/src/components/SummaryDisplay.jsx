import { useState, useEffect } from 'react'
import { exportExecutiveBrief } from '../services/api.js'

export default function SummaryDisplay({
  summary,
  mode,
  length,
  filename,
  documentId,
  analytics,
}) {
  const [copied, setCopied] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [showAttributions, setShowAttributions] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  if (!summary) return null

  const wordCount = summary.trim() ? summary.trim().split(/\s+/).length : 0

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(summary)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
    }
  }

  const handleDownload = () => {
    const blob = new Blob([summary], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const baseName = filename ? filename.replace(/\.[^/.]+$/, '') : 'document'
    link.href = url
    link.download = `${baseName}_summary_${mode}_${length}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleExportBrief = async () => {
    if (!documentId) return
    setIsExporting(true)
    try {
      const res = await exportExecutiveBrief({
        document_id: documentId,
        mode,
        length,
      })
      const blob = new Blob([res.html], { type: 'text/html;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      const baseName = filename ? filename.replace(/\.[^/.]+$/, '') : 'document'
      link.href = url
      link.download = `${baseName}_executive_brief_${mode}.html`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(`Export failed: ${err.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  const handleSpeech = () => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported by your browser.')
      return
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      return
    }

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(summary)
    utterance.rate = 1.0
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  const readability = analytics?.readability
  const keyphrases = analytics?.keyphrases || []
  const faithfulness = analytics?.faithfulness

  const modeBadge = {
    extractive: { label: 'Extractive', color: 'bg-blue-50 text-blue-700 ring-blue-600/20' },
    abstractive: { label: 'Abstractive', color: 'bg-purple-50 text-purple-700 ring-purple-600/20' },
    hybrid: { label: 'Hybrid', color: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20' },
  }[mode] || { label: mode, color: 'bg-slate-50 text-slate-700 ring-slate-600/20' }

  return (
    <section className="space-y-5 rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-7 shadow-xs">
      {/* Top Header & Actions Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h3 className="text-lg font-bold text-slate-900">Generated Summary</h3>
            <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${modeBadge.color}`}>
              {modeBadge.label}
            </span>
            {faithfulness && (
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                  faithfulness.hallucination_risk === 'low'
                    ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20'
                    : faithfulness.hallucination_risk === 'medium'
                    ? 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20'
                    : 'bg-rose-50 text-rose-700 ring-1 ring-rose-600/20'
                }`}
                title={`Factuality Confidence: ${faithfulness.overall_confidence}%`}
              >
                <span>🛡️</span> {faithfulness.overall_confidence}% Grounded
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Target Length: <span className="font-semibold text-slate-700 capitalize">{length}</span> &middot;{' '}
            <span className="font-semibold text-slate-700">{wordCount}</span> words
          </p>
        </div>

        {/* Action Buttons Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleSpeech}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition active:scale-95 ${
              isSpeaking
                ? 'border-indigo-600 bg-indigo-600 text-white animate-pulse'
                : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-300 hover:text-indigo-600 shadow-2xs'
            }`}
            title={isSpeaking ? 'Stop playback' : 'Listen to summary audio via TTS'}
          >
            <span>{isSpeaking ? '⏹' : '🔊'}</span>
            <span>{isSpeaking ? 'Stop Audio' : 'Listen'}</span>
          </button>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:border-slate-300 hover:bg-slate-50 active:scale-95"
          >
            <span>{copied ? '✓' : '📋'}</span>
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            type="button"
            onClick={handleDownload}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:border-slate-300 hover:bg-slate-50 active:scale-95"
            title="Download plain text"
          >
            ⬇ .txt
          </button>

          {documentId && (
            <button
              type="button"
              disabled={isExporting}
              onClick={handleExportBrief}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-indigo-700 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-50 active:scale-95"
              title="Download publication-ready Executive Summary Report (HTML/PDF)"
            >
              <span>📄</span>
              <span>{isExporting ? 'Exporting…' : 'Executive Report'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Key Topical Themes / Badges */}
      {keyphrases.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Topical Themes:
          </span>
          {keyphrases.map((tag, i) => (
            <span
              key={i}
              className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Readability & Quality Analytics Grid */}
      {readability && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-xl border border-slate-200/80 bg-gradient-to-b from-slate-50/80 to-slate-100/50 p-4">
          <div className="rounded-lg bg-white p-3 shadow-2xs border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Reading Time Saved
            </p>
            <p className="mt-1 text-lg font-extrabold text-indigo-600">
              {readability.time_saved_percent}%
            </p>
            <p className="text-[11px] text-slate-500">
              ~{readability.time_saved_seconds}s saved
            </p>
          </div>

          <div className="rounded-lg bg-white p-3 shadow-2xs border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Flesch Reading Ease
            </p>
            <p className="mt-1 text-lg font-extrabold text-slate-800">
              {readability.summary?.flesch_reading_ease}
              <span className="text-xs font-normal text-slate-400"> / 100</span>
            </p>
            <p className="text-[11px] text-slate-500 truncate" title={readability.summary?.reading_level}>
              {readability.summary?.reading_level}
            </p>
          </div>

          <div className="rounded-lg bg-white p-3 shadow-2xs border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              F-K Grade Level
            </p>
            <p className="mt-1 text-lg font-extrabold text-slate-800">
              Grade {readability.summary?.grade_level}
            </p>
            <p className="text-[11px] text-slate-500">
              {readability.ease_improvement >= 0 ? '+' : ''}
              {readability.ease_improvement} ease shift
            </p>
          </div>

          <div className="rounded-lg bg-white p-3 shadow-2xs border border-slate-100">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Factuality Guard
            </p>
            <p className="mt-1 text-lg font-extrabold text-emerald-600">
              {faithfulness?.overall_confidence || 100}%
            </p>
            <p className="text-[11px] text-slate-500">
              {faithfulness?.grounded_count || 0} of {faithfulness?.total_summary_sentences || 0} grounded
            </p>
          </div>
        </div>
      )}

      {/* Main Prose Summary Content */}
      <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-5.5 sm:p-6">
        <div className="prose-summary whitespace-pre-wrap leading-relaxed text-slate-800 text-[15px]">
          {summary}
        </div>
      </div>

      {/* Explainable AI: Source Attribution Alignment Drawer */}
      {faithfulness?.sentence_attributions?.length > 0 && (
        <div className="border-t border-slate-100 pt-4">
          <button
            type="button"
            onClick={() => setShowAttributions(!showAttributions)}
            className="flex items-center gap-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition"
          >
            <span>{showAttributions ? '▲ Hide' : '▼ View'} Sentence-Level Source Alignment &amp; Faithfulness</span>
            <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
              Explainable AI
            </span>
          </button>

          {showAttributions && (
            <div className="mt-3.5 space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
              <p className="text-xs text-slate-500">
                Each summary sentence is cross-checked against source document sentences using 384-dimensional dense semantic embeddings.
              </p>
              <div className="space-y-2.5">
                {faithfulness.sentence_attributions.map((attr, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-200 bg-white p-3.5 text-xs shadow-2xs space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
                      <span className="font-bold text-slate-900">
                        Summary Sentence #{idx + 1}
                      </span>
                      <span
                        className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          attr.is_grounded
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        {Math.round(attr.similarity * 100)}% Match {attr.is_grounded ? '(Grounded)' : '(Paraphrased)'}
                      </span>
                    </div>
                    <p className="text-slate-800 font-medium">{attr.summary_sentence}</p>
                    <div className="rounded-lg bg-slate-50 p-2.5 text-[11px] text-slate-600 italic border-l-2 border-indigo-500">
                      <strong className="text-slate-700 not-italic">Source Anchor [Sentence #{attr.source_sentence_index + 1}]:</strong> &ldquo;{attr.source_sentence}&rdquo;
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
