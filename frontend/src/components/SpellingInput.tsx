import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import { bind, unbind } from 'wanakana'
import * as Hangul from 'hangul-js'

interface Props {
  disabled: boolean
  correct?: boolean
  romajiInput?: boolean
  hangulInput?: boolean
  onSubmit: (value: string) => void
}

// 2-beolsik (두벌식) layout: the standard Korean-keyboard mapping from
// English-keyboard keys to Jamo, the same one Windows/Mac Korean IME uses.
// Hangul.assemble() composes a flat array of these into proper syllables.
const HANGUL_BASE_MAP: Record<string, string> = {
  q: 'ㅂ',
  w: 'ㅈ',
  e: 'ㄷ',
  r: 'ㄱ',
  t: 'ㅅ',
  y: 'ㅛ',
  u: 'ㅕ',
  i: 'ㅑ',
  o: 'ㅐ',
  p: 'ㅔ',
  a: 'ㅁ',
  s: 'ㄴ',
  d: 'ㅇ',
  f: 'ㄹ',
  g: 'ㅎ',
  h: 'ㅗ',
  j: 'ㅓ',
  k: 'ㅏ',
  l: 'ㅣ',
  z: 'ㅋ',
  x: 'ㅌ',
  c: 'ㅊ',
  v: 'ㅍ',
  b: 'ㅠ',
  n: 'ㅜ',
  m: 'ㅡ',
}
const HANGUL_SHIFT_MAP: Record<string, string> = {
  Q: 'ㅃ',
  W: 'ㅉ',
  E: 'ㄸ',
  R: 'ㄲ',
  T: 'ㅆ',
  O: 'ㅒ',
  P: 'ㅖ',
}

export default function SpellingInput({
  disabled,
  correct,
  romajiInput,
  hangulInput,
  onSubmit,
}: Props) {
  const [value, setValue] = useState('')
  const [hangulKeys, setHangulKeys] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const hangulValue = Hangul.assemble(hangulKeys)

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
    const text = (romajiInput ? inputRef.current?.value : hangulInput ? hangulValue : value) ?? ''
    if (disabled || !text.trim()) return
    onSubmit(text)
  }

  // Hangul mode composes Jamo from our own keystroke buffer rather than
  // wanakana-style DOM ownership, since every keystroke must map through
  // the 2-beolsik layout before it means anything -- so it stays a normal
  // React-controlled input (with `readOnly` since typing never mutates the
  // DOM value directly).
  function handleHangulKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      handleSubmit()
      return
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return
    if (e.key === 'Backspace') {
      e.preventDefault()
      setHangulKeys((keys) => keys.slice(0, -1))
      return
    }
    if (e.key.length === 1) {
      e.preventDefault()
      if (e.key === ' ') {
        setHangulKeys((keys) => [...keys, ' '])
        return
      }
      // Unmapped keys (digits, punctuation) are swallowed so the field only
      // ever contains Hangul.
      const jamo = HANGUL_BASE_MAP[e.key] ?? HANGUL_SHIFT_MAP[e.key]
      if (jamo) setHangulKeys((keys) => [...keys, jamo])
    }
  }

  const stateClass =
    correct === undefined
      ? 'border-gray-200 focus:border-sky-400 text-gray-700'
      : correct
        ? 'border-green-500 bg-green-50 text-green-800 animate-pulse_correct'
        : 'border-red-400 bg-red-50 text-red-800 animate-shake'

  const placeholder = romajiInput
    ? 'Type romaji, e.g. kanji…'
    : hangulInput
      ? 'Type using an English keyboard (2-beolsik)…'
      : 'Type your answer…'

  return (
    <div className="flex gap-2">
      <input
        ref={inputRef}
        type="text"
        value={romajiInput ? undefined : hangulInput ? hangulValue : value}
        readOnly={hangulInput}
        onChange={romajiInput || hangulInput ? undefined : (e) => setValue(e.target.value)}
        disabled={disabled}
        onKeyDown={(e) => {
          if (hangulInput) {
            handleHangulKeyDown(e)
            return
          }
          if (e.key === 'Enter') handleSubmit()
        }}
        placeholder={placeholder}
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
