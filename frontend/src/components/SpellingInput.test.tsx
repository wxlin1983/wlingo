import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
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
})
