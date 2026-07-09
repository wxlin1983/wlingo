import { useState, useRef, useEffect } from 'react'
import { bind, unbind } from 'wanakana'

interface Props {
  disabled: boolean
  correct?: boolean
  romajiInput?: boolean
  onSubmit: (value: string) => void
}

export default function SpellingInput({ disabled, correct, romajiInput, onSubmit }: Props) {
  const [value, setValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // wanakana owns the DOM input's value directly for live romaji->kana
  // conversion, which would fight a React-controlled value/onChange pair --
  // so this input is uncontrolled whenever romajiInput is on.
  useEffect(() => {
    if (!romajiInput || !inputRef.current) return
    const el = inputRef.current
    bind(el)
    return () => unbind(el)
  }, [romajiInput])

  function handleSubmit() {
    const text = (romajiInput ? inputRef.current?.value : value) ?? ''
    if (disabled || !text.trim()) return
    onSubmit(text)
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
        value={romajiInput ? undefined : value}
        onChange={romajiInput ? undefined : (e) => setValue(e.target.value)}
        disabled={disabled}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit()
        }}
        placeholder={romajiInput ? 'Type romaji, e.g. kanji…' : 'Type your answer…'}
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
