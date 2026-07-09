import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from './api'

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('api', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  it('topics() resolves with the parsed JSON body on success', async () => {
    const topics = [{ id: 'English', name: 'English', count: 10 }]
    vi.mocked(fetch).mockResolvedValue(jsonResponse(topics))

    await expect(api.topics()).resolves.toEqual(topics)
    expect(fetch).toHaveBeenCalledWith('/api/topics', undefined)
  })

  it('throws the response detail message when the request fails', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({ detail: 'Unknown topic' }, { status: 400, statusText: 'Bad Request' }),
    )

    await expect(api.topics()).rejects.toThrow('Unknown topic')
  })

  it('falls back to the status text when the error body has no detail', async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response('not json', { status: 500, statusText: 'Server Error' }),
    )

    await expect(api.topics()).rejects.toThrow('500 Server Error')
  })

  it('question() requests the given index', async () => {
    const question = { word: 'hello', options: ['a', 'b'], current_index: 2, total_questions: 5 }
    vi.mocked(fetch).mockResolvedValue(jsonResponse(question))

    await api.question(2)
    expect(fetch).toHaveBeenCalledWith('/api/quiz/2', undefined)
  })

  it('start() posts form-encoded topic/mode without following the redirect', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 302 }))

    await api.start('English', 'adaptive')

    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('/start')
    expect(init?.method).toBe('POST')
    expect(init?.redirect).toBe('manual')
    expect(String(init?.body)).toBe('topic=English&mode=adaptive')
  })

  it('submit() sends selected_option_index for a multiple-choice answer', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        word: 'hello',
        user_answer: '你好',
        correct_answer: '你好',
        is_correct: true,
        explanation: '',
      }),
    )

    await api.submit({ optionIndex: 2 }, 0)

    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toBe('/submit_answer')
    expect(init?.method).toBe('POST')
    const body = new URLSearchParams(String(init?.body))
    expect(body.get('selected_option_index')).toBe('2')
    expect(body.get('current_index')).toBe('0')
    expect(body.has('typed_answer')).toBe(false)
  })

  it('submit() sends typed_answer for a spelling answer', async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse({
        word: '你好',
        user_answer: 'hello',
        correct_answer: 'hello',
        is_correct: true,
        explanation: '',
      }),
    )

    await api.submit({ typedAnswer: 'hello' }, 3)

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = new URLSearchParams(String(init?.body))
    expect(body.get('typed_answer')).toBe('hello')
    expect(body.get('current_index')).toBe('3')
    expect(body.has('selected_option_index')).toBe(false)
  })

  it('reset() resolves on success', async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ status: 'success' }))

    await expect(api.reset()).resolves.toEqual({ status: 'success' })
  })

  it('reset() throws instead of silently succeeding when the request fails', async () => {
    // Regression test: reset() used to call the bare `fetch` and never
    // check `res.ok`, so a failed reset looked identical to a successful
    // one to every caller.
    vi.mocked(fetch).mockResolvedValue(
      new Response('{}', { status: 500, statusText: 'Server Error' }),
    )

    await expect(api.reset()).rejects.toThrow('500 Server Error')
  })
})
