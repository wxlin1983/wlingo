interface Props {
  value: 'adaptive' | 'random'
  onChange: (v: 'adaptive' | 'random') => void
}

const modes: { value: 'adaptive' | 'random'; label: string; desc: string }[] = [
  { value: 'adaptive', label: 'Adaptive', desc: 'Focuses on your weak spots' },
  { value: 'random',   label: 'Random',   desc: 'Pure shuffle' },
]

export default function ModeToggle({ value, onChange }: Props) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-600 mb-2">Quiz Mode</label>
      <div className="flex gap-3">
        {modes.map(m => {
          const active = value === m.value
          return (
            <label
              key={m.value}
              className={`flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border-2 cursor-pointer transition-all select-none ${
                active
                  ? 'border-sky-500 bg-sky-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input
                type="radio"
                name="mode"
                value={m.value}
                checked={active}
                onChange={() => onChange(m.value)}
                className="sr-only"
              />
              <span
                className={`w-4 h-4 rounded-full border-2 flex-shrink-0 transition-colors ${
                  active ? 'border-sky-500 bg-sky-500' : 'border-gray-300 bg-white'
                }`}
              />
              <div>
                <p className={`text-sm font-semibold ${active ? 'text-sky-700' : 'text-gray-700'}`}>
                  {m.label}
                </p>
                <p className="text-xs text-gray-400">{m.desc}</p>
              </div>
            </label>
          )
        })}
      </div>
    </div>
  )
}
