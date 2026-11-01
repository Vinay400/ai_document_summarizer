import { useState, useEffect } from 'react'

export default function ComparisonMatrix({
  comparisonData,
  filename,
  onEvaluate,
  isEvaluating,
  evaluationMetrics,
}) {
  const [viewLayout, setViewLayout] = useState('grid') // 'grid' | 'tabs'
  const [activeTab, setActiveTab] = useState('extractive')
  const [copiedMode, setCopiedMode] = useState(null)
  const [speakingMode, setSpeakingMode] = useState(null)
  const [referenceText, setReferenceText] = useState('')
  const [evalError, setEvalError] = useState(null)
  const [isEvalOpen, setIsEvalOpen] = useState(false)

  // Clean up speech synthesis if component unmounts
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  if (!comparisonData || !comparisonData.modes) return null

  const { modes, original_word_count, length } = comparisonData

  const strategyMeta = {
    extractive: {
      title: 'Extractive',
      model: 'all-MiniLM-L6-v2 + TextRank',
      badgeClass: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800',
      tagline: '100% Factually Grounded (Zero Hallucination)',
      accentBorder: 'border-t-blue-500',
      description: 'Selects the most statistically central sentences verbatim from source.',
    },
    abstractive: {
      title: 'Abstractive',
      model: 'facebook/bart-large-cnn (Map-Reduce)',
      badgeClass: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800',
      tagline: 'Fluent Human-Like Synthesis',
      accentBorder: 'border-t-purple-500',
      description: 'Generates new sentences and condenses high-level meaning.',
    },
    hybrid: {
      title: 'Hybrid',
      model: 'TextRank Filter → BART Condensation',
      badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800',
      tagline: 'Balanced Factual Filter + Neural Rewriting',
      accentBorder: 'border-t-emerald-500',
      description: 'Pre-filters core sentences before passing them to neural generation.',
    },
  }

  const handleCopy = async (modeKey, text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedMode(modeKey)
      setTimeout(() => setCopiedMode(null), 2000)
    } catch {
      // Fallback
    }
  }

  const handleDownload = (modeKey, text) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const baseName = filename ? filename.replace(/\.[^/.]+$/, '') : 'document'
    link.href = url
    link.download = `${baseName}_summary_${modeKey}_${length}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleSpeech = (modeKey, text) => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported by your browser.')
      return
    }

    if (speakingMode === modeKey) {
      window.speechSynthesis.cancel()
      setSpeakingMode(null)
      return
    }

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.0
    utterance.onend = () => setSpeakingMode(null)
    utterance.onerror = () => setSpeakingMode(null)

    setSpeakingMode(modeKey)
    window.speechSynthesis.speak(utterance)
  }

  const handleEvaluateSubmit = (e) => {
    e.preventDefault()
    if (!referenceText.trim()) {
      setEvalError('Please provide a ground-truth reference summary to score against.')
      return
    }
    setEvalError(null)

    // Collect precomputed summaries to send along
    const summariesPayload = {
      extractive: modes.extractive?.summary || '',
      abstractive: modes.abstractive?.summary || '',
      hybrid: modes.hybrid?.summary || '',
    }

    if (onEvaluate) {
      onEvaluate(referenceText.trim(), summariesPayload)
    }
  }

  // Find best score for each metric across the evaluated modes
  const findBestMetric = (metricKey) => {
    if (!evaluationMetrics) return null
    let bestVal = -1
    let bestMode = null
    Object.entries(evaluationMetrics).forEach(([mKey, data]) => {
      const val = data?.metrics?.[metricKey]
      if (typeof val === 'number' && val > bestVal) {
        bestVal = val
        bestMode = mKey
      }
    })
    return { bestMode, bestVal }
  }

  const modeKeys = ['extractive', 'abstractive', 'hybrid']

  return (
    <section className="space-y-6">
      {/* Main Container Header */}
      <div className="rounded-xl border border-edge bg-surface p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-edge pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10 text-xs font-bold text-accent">
                ⚡
              </span>
              <h3 className="text-lg font-semibold tracking-tight text-ink">
                3-Way Multi-Strategy Comparison
              </h3>
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              Side-by-side analysis of Extractive, Abstractive, and Hybrid summaries generated from{' '}
              <span className="font-semibold text-ink">{filename}</span> ({original_word_count?.toLocaleString()} words) at{' '}
              <span className="font-semibold capitalize text-ink">{length}</span> length.
            </p>
          </div>

          {/* Layout Switcher */}
          <div className="flex items-center gap-1 rounded-lg border border-edge bg-surface-sunken p-1 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setViewLayout('grid')}
              className={`rounded px-3 py-1 text-xs font-medium transition ${
                viewLayout === 'grid'
                  ? 'bg-surface text-ink shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              ⊞ 3-Column Grid
            </button>
            <button
              type="button"
              onClick={() => setViewLayout('tabs')}
              className={`rounded px-3 py-1 text-xs font-medium transition ${
                viewLayout === 'tabs'
                  ? 'bg-surface text-ink shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              ☰ Tabbed View
            </button>
          </div>
        </div>

        {/* Tab Selector when in Tabbed View */}
        {viewLayout === 'tabs' && (
          <div className="mt-4 flex gap-2 border-b border-edge pb-3">
            {modeKeys.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setActiveTab(k)}
                className={`rounded-lg px-4 py-2 text-xs font-semibold capitalize transition ${
                  activeTab === k
                    ? 'bg-accent text-white shadow-sm'
                    : 'bg-surface-sunken text-ink-muted hover:text-ink hover:bg-edge/40'
                }`}
              >
                {k} ({modes[k]?.word_count} words)
              </button>
            ))}
          </div>
        )}

        {/* Strategy Comparison Cards */}
        <div
          className={`mt-6 ${
            viewLayout === 'grid'
              ? 'grid grid-cols-1 gap-5 lg:grid-cols-3'
              : 'block'
          }`}
        >
          {modeKeys
            .filter((k) => viewLayout === 'grid' || activeTab === k)
            .map((k) => {
              const item = modes[k]
              const meta = strategyMeta[k]
              if (!item) return null

              const isSpeaking = speakingMode === k
              const isCopied = copiedMode === k

              return (
                <div
                  key={k}
                  className={`flex flex-col justify-between rounded-xl border border-edge bg-surface shadow-sm border-t-4 ${meta.accentBorder} transition hover:shadow-md`}
                >
                  <div className="p-5">
                    {/* Strategy header */}
                    <div className="flex items-start justify-between gap-2 border-b border-edge pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-ink">
                            {meta.title}
                          </h4>
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${meta.badgeClass}`}
                          >
                            {meta.title}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] font-medium text-ink-muted">
                          {meta.model}
                        </p>
                      </div>
                    </div>

                    {/* Stat Badges */}
                    <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                      <div className="rounded-lg bg-surface-sunken p-2">
                        <span className="block text-[10px] font-semibold uppercase text-ink-subtle">
                          Words
                        </span>
                        <span className="mt-0.5 block text-xs font-bold text-ink">
                          {item.word_count}
                        </span>
                      </div>
                      <div className="rounded-lg bg-surface-sunken p-2">
                        <span className="block text-[10px] font-semibold uppercase text-ink-subtle">
                          Reduction
                        </span>
                        <span className="mt-0.5 block text-xs font-bold text-ok">
                          {item.compression_ratio}%
                        </span>
                      </div>
                      <div className="rounded-lg bg-surface-sunken p-2">
                        <span className="block text-[10px] font-semibold uppercase text-ink-subtle">
                          Latency
                        </span>
                        <span className="mt-0.5 block text-xs font-bold text-accent">
                          {item.latency_seconds}s
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 rounded-md bg-surface-sunken/60 px-2.5 py-1.5 text-[11px] text-ink-muted italic">
                      {meta.tagline}
                    </div>

                    {/* Text Body */}
                    <div className="prose-summary mt-4 max-h-[360px] overflow-y-auto pr-1 text-xs leading-relaxed text-ink whitespace-pre-wrap">
                      {item.summary}
                    </div>
                  </div>

                  {/* Card Action Footer */}
                  <div className="flex items-center justify-between border-t border-edge bg-surface-sunken/50 p-3">
                    <button
                      type="button"
                      onClick={() => handleSpeech(k, item.summary)}
                      className={`flex items-center gap-1 rounded-md border border-edge px-2.5 py-1 text-xs font-medium transition ${
                        isSpeaking
                          ? 'border-accent bg-accent text-white animate-pulse'
                          : 'bg-surface text-ink hover:bg-surface-sunken'
                      }`}
                      title={isSpeaking ? 'Stop playback' : 'Listen to summary'}
                    >
                      {isSpeaking ? '⏹ Stop' : '▶ Listen'}
                    </button>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleCopy(k, item.summary)}
                        className="rounded-md border border-edge bg-surface px-2.5 py-1 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
                      >
                        {isCopied ? '✓ Copied' : 'Copy'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDownload(k, item.summary)}
                        className="rounded-md border border-edge bg-surface px-2.5 py-1 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
                        title="Download text file"
                      >
                        Download
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
        </div>
      </div>

      {/* Comparative Evaluation Section */}
      <div className="rounded-xl border border-edge bg-surface p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-ink">
              Multi-Strategy Evaluation (ROUGE &amp; BLEU Benchmark)
            </h3>
            <p className="mt-0.5 text-xs text-ink-muted">
              Benchmark all three summarization methods against a single ground-truth reference summary.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setIsEvalOpen(!isEvalOpen)}
            className="text-xs font-semibold text-accent hover:underline"
          >
            {isEvalOpen ? '▲ Collapse Reference Form' : '▼ Expand Reference Form'}
          </button>
        </div>

        {/* Ground Truth Reference Form */}
        {isEvalOpen && (
          <form onSubmit={handleEvaluateSubmit} className="mt-4 space-y-3 border-t border-edge pt-4">
            <div>
              <label
                htmlFor="compare-reference-summary"
                className="block text-xs font-semibold uppercase tracking-wide text-ink-subtle"
              >
                Ground Truth Reference Summary
              </label>
              <textarea
                id="compare-reference-summary"
                rows={4}
                value={referenceText}
                onChange={(e) => setReferenceText(e.target.value)}
                placeholder="Paste human-written or ideal benchmark summary here..."
                disabled={isEvaluating}
                className="mt-1 w-full rounded-lg border border-edge bg-surface-sunken p-3 text-sm text-ink placeholder:text-ink-subtle focus:border-accent focus:bg-surface focus:outline-none"
              />
            </div>

            {evalError && <p className="text-xs text-danger">{evalError}</p>}

            <button
              type="submit"
              disabled={isEvaluating}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-accent-strong disabled:opacity-60"
            >
              {isEvaluating ? (
                <>
                  <svg className="h-3.5 w-3.5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Evaluating All 3 Modes…
                </>
              ) : (
                'Score All 3 Modes Against Reference'
              )}
            </button>
          </form>
        )}

        {/* Side-by-Side Evaluation Table */}
        {evaluationMetrics && (
          <div className="mt-6 space-y-4 border-t border-edge pt-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                Comparative Metrics Scorecard
              </h4>
              <span className="text-[11px] text-ink-muted">
                ★ Best performer highlighted per metric
              </span>
            </div>

            <div className="overflow-x-auto rounded-lg border border-edge">
              <table className="w-full text-left text-xs text-ink">
                <thead className="border-b border-edge bg-surface-sunken text-ink-muted">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Evaluation Metric</th>
                    <th className="px-4 py-3 font-semibold text-blue-600 dark:text-blue-400">
                      Extractive
                    </th>
                    <th className="px-4 py-3 font-semibold text-purple-600 dark:text-purple-400">
                      Abstractive
                    </th>
                    <th className="px-4 py-3 font-semibold text-emerald-600 dark:text-emerald-400">
                      Hybrid
                    </th>
                    <th className="px-4 py-3 font-semibold">Scale</th>
                    <th className="px-4 py-3 font-semibold">Significance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-edge">
                  {[
                    {
                      key: 'rouge_1',
                      name: 'ROUGE-1',
                      scale: '0.0 – 1.0',
                      desc: 'Unigram word overlap F1-score',
                      format: (v) => v?.toFixed(4),
                    },
                    {
                      key: 'rouge_2',
                      name: 'ROUGE-2',
                      scale: '0.0 – 1.0',
                      desc: 'Bigram phrase overlap F1-score',
                      format: (v) => v?.toFixed(4),
                    },
                    {
                      key: 'rouge_l',
                      name: 'ROUGE-L',
                      scale: '0.0 – 1.0',
                      desc: 'Longest common subsequence structure',
                      format: (v) => v?.toFixed(4),
                    },
                    {
                      key: 'bleu',
                      name: 'BLEU',
                      scale: '0 – 100',
                      desc: 'N-gram precision & fluency score',
                      format: (v) => v?.toFixed(2),
                    },
                  ].map((metric) => {
                    const best = findBestMetric(metric.key)
                    return (
                      <tr key={metric.key} className="hover:bg-surface-sunken/40">
                        <td className="px-4 py-3 font-medium text-ink">
                          {metric.name}
                        </td>
                        {modeKeys.map((mk) => {
                          const val = evaluationMetrics[mk]?.metrics?.[metric.key]
                          const isBest = best?.bestMode === mk && val > 0
                          return (
                            <td key={mk} className="px-4 py-3 font-mono">
                              <span
                                className={`inline-flex items-center gap-1 font-bold ${
                                  isBest
                                    ? 'text-ok bg-ok-soft px-2 py-0.5 rounded'
                                    : 'text-ink'
                                }`}
                              >
                                {val !== undefined ? metric.format(val) : '—'}
                                {isBest && (
                                  <span className="text-[10px] text-ok" title="Highest score">
                                    ★
                                  </span>
                                )}
                              </span>
                            </td>
                          )
                        })}
                        <td className="px-4 py-3 text-ink-muted">{metric.scale}</td>
                        <td className="px-4 py-3 text-ink-muted">{metric.desc}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Analysis & Viva Insight callout */}
            <div className="rounded-lg border border-accent/20 bg-accent-soft/30 p-4 text-xs leading-relaxed text-ink-muted">
              <p className="font-semibold text-accent">
                💡 Analysis &amp; Viva Discussion Note:
              </p>
              <p className="mt-1">
                Notice how the three approaches behave differently: <strong>Extractive</strong> guarantees zero factual hallucination by directly quoting sentences; <strong>Abstractive</strong> achieves higher linguistic cohesion and rephrasing; and <strong>Hybrid</strong> uses TextRank as a factual filter before BART condensation to balance high factual fidelity with fluent readability.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
