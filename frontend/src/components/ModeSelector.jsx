const MODES = [
  {
    id: 'extractive',
    name: 'Extractive',
    description:
      'Quotes key sentences verbatim from the source; cannot invent facts or hallucinate.',
  },
  {
    id: 'abstractive',
    name: 'Abstractive',
    description:
      'Rewrites and synthesizes concepts in fluent prose; creates new sentences but may hallucinate.',
  },
  {
    id: 'hybrid',
    name: 'Hybrid',
    description:
      'Combines both: pre-filters key sentences with TextRank then condenses them with BART.',
  },
]

export default function ModeSelector({ value, onChange, disabled }) {
  return (
    <div className="space-y-2">
      <label className="block text-xs font-semibold uppercase tracking-wide text-ink-subtle">
        Summarization Mode
      </label>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {MODES.map((mode) => {
          const isSelected = value === mode.id
          return (
            <label
              key={mode.id}
              className={`flex cursor-pointer flex-col justify-between rounded-xl border p-4 transition ${
                disabled ? 'cursor-not-allowed opacity-60' : ''
              } ${
                isSelected
                  ? 'border-accent bg-accent-soft/40 shadow-sm'
                  : 'border-edge bg-surface hover:border-edge-strong'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-ink">{mode.name}</span>
                <input
                  type="radio"
                  name="summarization-mode"
                  value={mode.id}
                  checked={isSelected}
                  onChange={() => onChange(mode.id)}
                  disabled={disabled}
                  className="h-4 w-4 accent-accent"
                />
              </div>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                {mode.description}
              </p>
            </label>
          )
        })}
      </div>
    </div>
  )
}
