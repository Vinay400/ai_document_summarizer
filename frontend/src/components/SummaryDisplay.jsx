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

  return (
    <section className="space-y-4 rounded-xl border border-edge bg-surface p-6 shadow-sm">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-ink">Generated Summary</h3>
            {faithfulness && (
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase ${
                  faithfulness.hallucination_risk === 'low'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                    : faithfulness.hallucination_risk === 'medium'
                    ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                }`}
                title={`Factuality Confidence: ${faithfulness.overall_confidence}%`}
              >
                ✓ {faithfulness.overall_confidence}% Grounded
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-ink-muted">
            Mode: <span className="font-medium capitalize text-ink">{mode}</span>{' '}
            &middot; Length:{' '}
            <span className="font-medium capitalize text-ink">{length}</span>{' '}
            &middot; {wordCount} words
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleSpeech}
            className={`flex items-center gap-1 rounded-md border border-edge px-3 py-1.5 text-xs font-medium transition ${
              isSpeaking
                ? 'border-accent bg-accent text-white animate-pulse'
                : 'bg-surface text-ink hover:bg-surface-sunken'
            }`}
            title={isSpeaking ? 'Stop playback' : 'Listen to summary audio'}
          >
            {isSpeaking ? '⏹ Stop Audio' : '▶ Listen'}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
          >
            .txt
          </button>
          {documentId && (
            <button
              type="button"
              disabled={isExporting}
              onClick={handleExportBrief}
              className="rounded-md border border-accent bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent hover:text-white disabled:opacity-50"
              title="Download formatted executive summary brief HTML/PDF report"
            >
              {isExporting ? 'Exporting…' : '📄 Executive Report'}
            </button>
          )}
        </div>
      </div>

      {/* Key Topical Themes / Tags */}
      {keyphrases.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">
            Topics:
          </span>
          {keyphrases.map((tag, i) => (
            <span
              key={i}
              className="rounded-md border border-edge bg-surface-sunken px-2 py-0.5 text-xs text-ink-muted"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Analytics Cards (Readability & Efficiency) */}
      {readability && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-lg border border-edge bg-surface-sunken p-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">
              Time Saved
            </p>
            <p className="mt-0.5 text-sm font-bold text-accent">
              {readability.time_saved_percent}%
            </p>
            <p className="text-[11px] text-ink-muted">
              ~{readability.time_saved_seconds}s saved
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">
              Reading Ease
            </p>
            <p className="mt-0.5 text-sm font-bold text-ink">
              {readability.summary?.flesch_reading_ease}
              <span className="text-xs text-ink-muted"> / 100</span>
            </p>
            <p className="text-[11px] text-ink-muted truncate">
              {readability.summary?.reading_level}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">
              F-K Grade Level
            </p>
            <p className="mt-0.5 text-sm font-bold text-ink">
              Grade {readability.summary?.grade_level}
            </p>
            <p className="text-[11px] text-ink-muted">
              {readability.ease_improvement >= 0 ? '+' : ''}
              {readability.ease_improvement} ease shift
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">
              Factuality Guard
            </p>
            <p className="mt-0.5 text-sm font-bold text-emerald-600 dark:text-emerald-400">
              {faithfulness?.overall_confidence || 100}%
            </p>
            <p className="text-[11px] text-ink-muted">
              {faithfulness?.grounded_count || 0} / {faithfulness?.total_summary_sentences || 0} grounded
            </p>
          </div>
        </div>
      )}

      {/* Main Summary Text */}
      <div className="prose-summary whitespace-pre-wrap leading-relaxed text-ink">
        {summary}
      </div>

      {/* Source Attribution & Alignment Drawer */}
      {faithfulness?.sentence_attributions?.length > 0 && (
        <div className="border-t border-edge pt-3">
          <button
            type="button"
            onClick={() => setShowAttributions(!showAttributions)}
            className="flex items-center gap-1.5 text-xs font-semibold text-accent hover:underline"
          >
            <span>{showAttributions ? '▲ Hide' : '▼ View'} Source Sentence Alignment &amp; Faithfulness</span>
            <span className="rounded bg-accent/10 px-1.5 py-0.2 text-[10px] text-accent">
              Explainable AI
            </span>
          </button>

          {showAttributions && (
            <div className="mt-3 space-y-3 rounded-lg border border-edge bg-surface-sunken p-3.5">
              <p className="text-xs text-ink-muted">
                Each summary sentence is cross-checked against source document sentences using semantic embeddings.
              </p>
              {faithfulness.sentence_attributions.map((attr, idx) => (
                <div
                  key={idx}
                  className="rounded-md border border-edge bg-surface p-2.5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-ink">
                      Summary Sentence {idx + 1}
                    </span>
                    <span
                      className={`font-mono text-[11px] font-medium ${
                        attr.is_grounded
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      {Math.round(attr.similarity * 100)}% Match {attr.is_grounded ? '(Grounded)' : '(Paraphrased)'}
                    </span>
                  </div>
                  <p className="text-ink">{attr.summary_sentence}</p>
                  <div className="rounded bg-surface-sunken p-2 text-[11px] text-ink-muted italic border-l-2 border-accent">
                    <strong>Source Anchor [Sentence #{attr.source_sentence_index + 1}]:</strong> &ldquo;{attr.source_sentence}&rdquo;
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
