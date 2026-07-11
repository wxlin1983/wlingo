import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SpellingInput from './SpellingInput'

const bindMock = vi.fn()
const unbindMock = vi.fn()
vi.mock('wanakana', () => ({
  bind: (...args: unknown[]) => bindMock(...args),
  unbind: (...args: unknown[]) => unbindMock(...args),
}))

describe('SpellingInput', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not bind wanakana when romajiInput is falsy', () => {
    render(<SpellingInput disabled={false} onSubmit={vi.fn()} />)
    expect(bindMock).not.toHaveBeenCalled()
  })

  it('is a normal controlled input when romajiInput is falsy', async () => {
    const user = userEvent.setup()
    render(<SpellingInput disabled={false} onSubmit={vi.fn()} />)

    const input = screen.getByPlaceholderText(/type your answer/i)
    await user.type(input, 'hello')
    expect(input).toHaveValue('hello')
  })

  it('binds wanakana to the input when romajiInput is true', () => {
    render(<SpellingInput disabled={false} romajiInput onSubmit={vi.fn()} />)

    expect(bindMock).toHaveBeenCalledTimes(1)
    expect(bindMock.mock.calls[0][0]).toBeInstanceOf(HTMLInputElement)
    expect(screen.getByPlaceholderText(/type romaji/i)).toBeInTheDocument()
  })

  it('unbinds wanakana on unmount', () => {
    const { unmount } = render(<SpellingInput disabled={false} romajiInput onSubmit={vi.fn()} />)
    expect(bindMock).toHaveBeenCalledTimes(1)
    unmount()
    expect(unbindMock).toHaveBeenCalledTimes(1)
  })

  it('submits the current input value on Enter when romajiInput is true', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<SpellingInput disabled={false} romajiInput onSubmit={onSubmit} />)

    const input = screen.getByPlaceholderText(/type romaji/i)
    await user.type(input, 'kanji{Enter}')

    expect(onSubmit).toHaveBeenCalledWith('kanji')
  })

  it('does not bind wanakana when hangulInput is true', () => {
    render(<SpellingInput disabled={false} hangulInput onSubmit={vi.fn()} />)
    expect(bindMock).not.toHaveBeenCalled()
    expect(screen.getByPlaceholderText(/english keyboard/i)).toHaveAttribute('readonly')
  })

  it('assembles 2-beolsik keystrokes into Hangul syllables', () => {
    render(<SpellingInput disabled={false} hangulInput onSubmit={vi.fn()} />)
    const input = screen.getByPlaceholderText(/english keyboard/i)

    for (const key of 'dkssud') fireEvent.keyDown(input, { key })

    expect(input).toHaveValue('안녕')
  })

  it('supports shifted keys for double consonants/vowels', () => {
    render(<SpellingInput disabled={false} hangulInput onSubmit={vi.fn()} />)
    const input = screen.getByPlaceholderText(/english keyboard/i)

    fireEvent.keyDown(input, { key: 'R', shiftKey: true })
    fireEvent.keyDown(input, { key: 'k' })

    expect(input).toHaveValue('까')
  })

  it('removes the last Jamo on Backspace, re-composing the syllable', () => {
    render(<SpellingInput disabled={false} hangulInput onSubmit={vi.fn()} />)
    const input = screen.getByPlaceholderText(/english keyboard/i)

    for (const key of 'dkssud') fireEvent.keyDown(input, { key })
    fireEvent.keyDown(input, { key: 'Backspace' })

    expect(input).toHaveValue('안녀')
  })

  it('ignores unmapped keys (digits, punctuation) in hangul mode', () => {
    render(<SpellingInput disabled={false} hangulInput onSubmit={vi.fn()} />)
    const input = screen.getByPlaceholderText(/english keyboard/i)

    fireEvent.keyDown(input, { key: '5' })
    fireEvent.keyDown(input, { key: 'd' })

    expect(input).toHaveValue('ㅇ')
  })

  it('submits the assembled Hangul value on Enter when hangulInput is true', () => {
    const onSubmit = vi.fn()
    render(<SpellingInput disabled={false} hangulInput onSubmit={onSubmit} />)
    const input = screen.getByPlaceholderText(/english keyboard/i)

    for (const key of 'dkssud') fireEvent.keyDown(input, { key })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onSubmit).toHaveBeenCalledWith('안녕')
  })
})
