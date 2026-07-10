interface Props {
  value: 'adaptive' | 'random'
  onChange: (v: 'adaptive' | 'random') => void
}

const modes: { value: 'adaptive' | 'random'; label: string; desc: string }[] = [
  { value: 'adaptive', label: 'Adaptive', desc: 'Focuses on your weak spots' },
  { value: 'random', label: 'Random', desc: 'Pure shuffle' },
]

export default function ModeToggle({ value, onChange }: Props) {
  const active = modes.find((m) => m.value === value) ?? modes[0]

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-sm font-semibold text-gray-600">Quiz Mode</span>
        <span className="text-xs text-gray-400">{active.desc}</span>
      </div>
      <div className="flex bg-gray-100 rounded-xl p-1" role="radiogroup" aria-label="Quiz mode">
        {modes.map((m) => {
          const isActive = value === m.value
          return (
            <button
              key={m.value}
              role="radio"
              aria-checked={isActive}
              onClick={() => onChange(m.value)}
              className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${
                isActive ? 'bg-white shadow text-sky-700' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              {m.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
