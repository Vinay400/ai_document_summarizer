const LENGTHS = [
  { id: 'short', name: 'Short' },
  { id: 'medium', name: 'Medium' },
  { id: 'long', name: 'Long' },
]

export default function LengthSelector({ value, onChange, disabled }) {
  return (
    <div className="space-y-2">
      <label className="block text-xs font-semibold uppercase tracking-wide text-ink-subtle">
        Target Summary Length
      </label>
      <div className="inline-flex rounded-lg border border-edge bg-surface-sunken p-1">
        {LENGTHS.map((len) => {
          const isSelected = value === len.id
          return (
            <button
              key={len.id}
              type="button"
              onClick={() => onChange(len.id)}
              disabled={disabled}
              className={`rounded-md px-4 py-1.5 text-xs font-medium transition ${
                disabled ? 'cursor-not-allowed opacity-60' : ''
              } ${
                isSelected
                  ? 'bg-surface text-ink shadow-sm'
                  : 'text-ink-muted hover:text-ink'
              }`}
            >
              {len.name}
            </button>
          )
        })}
      </div>
    </div>
  )
}
