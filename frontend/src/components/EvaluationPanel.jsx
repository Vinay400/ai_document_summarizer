import { useState } from 'react'

export default function EvaluationPanel({ onEvaluate, metrics, isEvaluating }) {
  const [isOpen, setIsOpen] = useState(false)
  const [reference, setReference] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!reference.trim()) {
      setError('Please enter a ground-truth reference summary to score against.')
      return
    }
    setError(null)
    onEvaluate(reference.trim())
  }

  return (
    <section className="rounded-2xl border border-slate-200/90 bg-white shadow-xs overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-5 sm:p-6 text-left transition hover:bg-slate-50/70"
      >
        <div className="flex items-center gap-3.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600 shadow-2xs">
            📊
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900">
                Evaluation Benchmark (ROUGE &amp; BLEU)
              </h3>
              <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-purple-700 ring-1 ring-inset ring-purple-700/20">
                Quality Scoring
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              Measure overlap and generation precision against a human reference summary
            </p>
          </div>
        </div>
        <span className="text-xs font-bold text-indigo-600">
          {isOpen ? '▲ Hide' : '▼ Expand'}
        </span>
      </button>

      {isOpen && (
        <div className="space-y-5 border-t border-slate-100 p-5 sm:p-6 bg-slate-50/30">
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label
                htmlFor="reference-summary"
                className="block text-xs font-bold uppercase tracking-wider text-slate-500"
              >
                Ground-Truth Reference Summary
              </label>
              <textarea
                id="reference-summary"
                rows={4}
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Paste human-written golden summary here to benchmark against..."
                disabled={isEvaluating}
                className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-3.5 text-sm text-slate-900 placeholder:text-slate-400 shadow-2xs focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-xs text-rose-600 font-medium">
                <span>⚠️</span> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isEvaluating}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-50 active:scale-95"
            >
              {isEvaluating ? 'Computing Metrics…' : 'Calculate ROUGE & BLEU'}
            </button>
          </form>

          {metrics && (
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Evaluation Scores
              </h4>
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs">
                <table className="w-full text-left text-xs text-slate-800">
                  <thead className="border-b border-slate-100 bg-slate-50/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <tr>
                      <th className="px-5 py-3">Metric</th>
                      <th className="px-5 py-3">Score</th>
                      <th className="px-5 py-3">Scale</th>
                      <th className="px-5 py-3">Evaluation Focus</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium">
                    <tr className="hover:bg-slate-50/50">
                      <td className="px-5 py-3.5 font-bold text-slate-900">ROUGE-1</td>
                      <td className="px-5 py-3.5 font-mono text-sm font-bold text-indigo-600">
                        {metrics.rouge_1.toFixed(4)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">0.0 &ndash; 1.0</td>
                      <td className="px-5 py-3.5 text-slate-600">
                        Unigram (single-word) overlap F1-score
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/50">
                      <td className="px-5 py-3.5 font-bold text-slate-900">ROUGE-2</td>
                      <td className="px-5 py-3.5 font-mono text-sm font-bold text-indigo-600">
                        {metrics.rouge_2.toFixed(4)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">0.0 &ndash; 1.0</td>
                      <td className="px-5 py-3.5 text-slate-600">
                        Bigram (two-word phrase) overlap F1-score
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/50">
                      <td className="px-5 py-3.5 font-bold text-slate-900">ROUGE-L</td>
                      <td className="px-5 py-3.5 font-mono text-sm font-bold text-indigo-600">
                        {metrics.rouge_l.toFixed(4)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">0.0 &ndash; 1.0</td>
                      <td className="px-5 py-3.5 text-slate-600">
                        Longest Common Subsequence sentence structure F1-score
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/50">
                      <td className="px-5 py-3.5 font-bold text-slate-900">BLEU</td>
                      <td className="px-5 py-3.5 font-mono text-sm font-bold text-indigo-600">
                        {metrics.bleu.toFixed(2)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">0 &ndash; 100</td>
                      <td className="px-5 py-3.5 text-slate-600">
                        Precision score for sentence generation fluency (sacrebleu)
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
