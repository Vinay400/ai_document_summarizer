import { useState } from 'react'

export default function SummaryDisplay({ summary, mode, length, filename }) {
  const [copied, setCopied] = useState(false)

  if (!summary) return null

  const wordCount = summary.trim() ? summary.trim().split(/\s+/).length : 0

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(summary)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback if clipboard API is blocked
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

  return (
    <section className="space-y-4 rounded-xl border border-edge bg-surface p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge pb-4">
        <div>
          <h3 className="text-base font-semibold text-ink">Generated Summary</h3>
          <p className="mt-0.5 text-xs text-ink-muted">
            Mode: <span className="font-medium capitalize text-ink">{mode}</span>{' '}
            &middot; Length:{' '}
            <span className="font-medium capitalize text-ink">{length}</span>{' '}
            &middot; {wordCount} words
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
          >
            {copied ? '✓ Copied' : 'Copy to Clipboard'}
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="rounded-md border border-edge bg-surface px-3 py-1.5 text-xs font-medium text-ink transition hover:border-edge-strong hover:bg-surface-sunken"
          >
            Download .txt
          </button>
        </div>
      </div>

      <div className="prose-summary whitespace-pre-wrap">{summary}</div>
    </section>
  )
}
