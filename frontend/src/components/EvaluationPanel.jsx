import { useState } from 'react'

export default function EvaluationPanel({ onEvaluate, metrics, isEvaluating }) {
  const [isOpen, setIsOpen] = useState(false)
  const [reference, setReference] = useState('')
  const [error, setError] = useState(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!reference.trim()) {
      setError('Please enter a reference summary to evaluate against.')
      return
    }
    setError(null)
    onEvaluate(reference.trim())
  }

  return (
    <section className="rounded-xl border border-edge bg-surface shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between p-6 text-left"
      >
        <div>
          <h3 className="text-base font-semibold text-ink">
            Evaluation (ROUGE &amp; BLEU)
          </h3>
          <p className="mt-0.5 text-xs text-ink-muted">
            Compare generated summary against a ground truth reference summary
          </p>
        </div>
        <span className="text-xs font-semibold text-accent">
          {isOpen ? '▲ Hide' : '▼ Expand'}
        </span>
      </button>

      {isOpen && (
        <div className="space-y-4 border-t border-edge p-6">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label
                htmlFor="reference-summary"
                className="block text-xs font-semibold uppercase tracking-wide text-ink-subtle"
              >
                Reference Summary (Ground Truth)
              </label>
              <textarea
                id="reference-summary"
                rows={4}
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Paste human-written or ideal summary here..."
                disabled={isEvaluating}
                className="mt-1 w-full rounded-lg border border-edge bg-surface-sunken p-3 text-sm text-ink placeholder:text-ink-subtle focus:border-accent focus:bg-surface focus:outline-none"
              />
            </div>

            {error && <p className="text-xs text-danger">{error}</p>}

            <button
              type="submit"
              disabled={isEvaluating}
              className="rounded-lg bg-accent px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-accent-strong disabled:opacity-60"
            >
              {isEvaluating ? 'Evaluating…' : 'Evaluate Summary'}
            </button>
          </form>

          {metrics && (
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                Evaluation Scores
              </h4>
              <div className="overflow-x-auto rounded-lg border border-edge">
                <table className="w-full text-left text-xs text-ink">
                  <thead className="border-b border-edge bg-surface-sunken text-ink-muted">
                    <tr>
                      <th className="px-4 py-2 font-semibold">Metric</th>
                      <th className="px-4 py-2 font-semibold">Score</th>
                      <th className="px-4 py-2 font-semibold">Scale</th>
                      <th className="px-4 py-2 font-semibold">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-edge">
                    <tr>
                      <td className="px-4 py-2 font-medium">ROUGE-1</td>
                      <td className="px-4 py-2 font-mono font-bold text-accent">
                        {metrics.rouge_1.toFixed(4)}
                      </td>
                      <td className="px-4 py-2 text-ink-muted">0.0 – 1.0</td>
                      <td className="px-4 py-2 text-ink-muted">
                        Unigram word overlap F1-score
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">ROUGE-2</td>
                      <td className="px-4 py-2 font-mono font-bold text-accent">
                        {metrics.rouge_2.toFixed(4)}
                      </td>
                      <td className="px-4 py-2 text-ink-muted">0.0 – 1.0</td>
                      <td className="px-4 py-2 text-ink-muted">
                        Bigram sequence overlap F1-score
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">ROUGE-L</td>
                      <td className="px-4 py-2 font-mono font-bold text-accent">
                        {metrics.rouge_l.toFixed(4)}
                      </td>
                      <td className="px-4 py-2 text-ink-muted">0.0 – 1.0</td>
                      <td className="px-4 py-2 text-ink-muted">
                        Longest Common Subsequence F1-score
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-2 font-medium">BLEU</td>
                      <td className="px-4 py-2 font-mono font-bold text-accent">
                        {metrics.bleu.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-ink-muted">0 – 100</td>
                      <td className="px-4 py-2 text-ink-muted">
                        Precision score for sentence generation
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
