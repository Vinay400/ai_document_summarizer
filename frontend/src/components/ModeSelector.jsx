const MODES = [
  {
    id: 'extractive',
    name: 'Extractive',
    icon: '🛡️',
    badge: '100% Factually Grounded',
    accentColor: 'blue',
    description: 'Picks statistically central sentences verbatim using MiniLM embeddings + TextRank. Cannot invent false facts.',
  },
  {
    id: 'abstractive',
    name: 'Abstractive',
    icon: '🧠',
    badge: 'Fluent Neural Rewriting',
    accentColor: 'purple',
    description: 'Generates new, concise sentences using facebook/bart-large-cnn. Synthesizes key concepts into natural prose.',
  },
  {
    id: 'hybrid',
    name: 'Hybrid Pipeline',
    icon: '⚡',
    badge: 'Best of Both Worlds',
    accentColor: 'emerald',
    description: 'Filters the top 50% salient sentences with TextRank, then feeds them to BART to condense with minimal hallucination.',
  },
]

export default function ModeSelector({ value, onChange, disabled }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Select Summarization Strategy
        </label>
        <span className="text-[11px] text-slate-400">
          Choose based on your factual fidelity needs
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
        {MODES.map((mode) => {
          const isSelected = value === mode.id
          return (
            <label
              key={mode.id}
              className={`relative flex cursor-pointer flex-col justify-between rounded-xl border p-4.5 transition-all duration-150 ${
                disabled ? 'cursor-not-allowed opacity-60' : 'hover:scale-[1.01]'
              } ${
                isSelected
                  ? mode.accentColor === 'blue'
                    ? 'border-blue-500 bg-blue-50/50 shadow-sm ring-1 ring-blue-500'
                    : mode.accentColor === 'purple'
                    ? 'border-purple-500 bg-purple-50/50 shadow-sm ring-1 ring-purple-500'
                    : 'border-emerald-500 bg-emerald-50/50 shadow-sm ring-1 ring-emerald-500'
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60 shadow-2xs'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{mode.icon}</span>
                    <span className="text-sm font-bold text-slate-900">{mode.name}</span>
                  </div>
                  <input
                    type="radio"
                    name="summarization-mode"
                    value={mode.id}
                    checked={isSelected}
                    onChange={() => onChange(mode.id)}
                    disabled={disabled}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                  />
                </div>

                <div className="mt-2.5">
                  <span
                    className={`inline-block rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      isSelected
                        ? mode.accentColor === 'blue'
                          ? 'bg-blue-100 text-blue-800'
                          : mode.accentColor === 'purple'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {mode.badge}
                  </span>
                </div>

                <p className="mt-2.5 text-xs leading-relaxed text-slate-600">
                  {mode.description}
                </p>
              </div>
            </label>
          )
        })}
      </div>
    </div>
  )
}
