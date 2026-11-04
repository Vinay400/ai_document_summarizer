const LENGTHS = [
  { id: 'short', name: 'Short (TL;DR)', detail: '~50-80 words' },
  { id: 'medium', name: 'Medium (Standard)', detail: '~110-160 words' },
  { id: 'long', name: 'Long (Detailed)', detail: '~180-260 words' },
]

export default function LengthSelector({ value, onChange, disabled }) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Target Output Length
        </label>
        <span className="text-[11px] text-slate-400">
          Controls beam generation token budget
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 rounded-xl border border-slate-200 bg-slate-100/70 p-1.5">
        {LENGTHS.map((len) => {
          const isSelected = value === len.id
          return (
            <button
              key={len.id}
              type="button"
              onClick={() => onChange(len.id)}
              disabled={disabled}
              className={`flex flex-col items-center justify-center rounded-lg py-2 px-3 text-xs font-medium transition-all duration-150 ${
                disabled ? 'cursor-not-allowed opacity-60' : ''
              } ${
                isSelected
                  ? 'bg-white text-indigo-700 font-bold shadow-xs ring-1 ring-slate-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
              }`}
            >
              <span>{len.name}</span>
              <span className={`text-[10px] ${isSelected ? 'text-indigo-500' : 'text-slate-400'}`}>
                {len.detail}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
