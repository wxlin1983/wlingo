import { useState, useRef, useEffect } from 'react'

interface Props {
  disabled: boolean
  correct?: boolean
  onSubmit: (value: string) => void
}

export default function SpellingInput({ disabled, correct, onSubmit }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  function handleSubmit() {
    if (disabled || !value.trim()) return
    onSubmit(value)
  }

  const stateClass =
    correct === undefined
      ? 'border-gray-200 focus:border-sky-400 text-gray-700'
      : correct
        ? 'border-green-500 bg-green-50 text-green-800 animate-pulse_correct'
        : 'border-red-400 bg-red-50 text-red-800 animate-shake'

  return (
    <div className="flex gap-2">
      <input
        ref={inputRef}
        type="text"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit()
        }}
        placeholder="Type your answer…"
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        className={`flex-1 px-4 py-3 rounded-xl border-2 text-lg text-center bg-white focus:outline-none disabled:opacity-70 transition-colors ${stateClass}`}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled}
        className="px-5 py-3 bg-sky-500 hover:bg-sky-600 text-white font-semibold rounded-xl disabled:opacity-50 transition-colors"
      >
        Submit
      </button>
    </div>
  )
}
