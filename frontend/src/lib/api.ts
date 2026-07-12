import type { Topic, Question, AnswerRecord, SessionInfo, QuizResult, WordStat } from './types'
import { ROOT_PATH as BASE } from './env'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init)
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  topics: () => json<Topic[]>('/api/topics'),

  session: () => json<SessionInfo>('/api/session'),

  question: (index: number) => json<Question>(`/api/quiz/${index}`),

  result: () => json<QuizResult>('/api/result'),

  wordStats: (topic: string) => json<WordStat[]>(`/api/word_stats/${encodeURIComponent(topic)}`),

  start: (topic: string, mode: string): Promise<Response> => {
    const body = new URLSearchParams({ topic, mode })
    // Use redirect:'manual' so the 302→session cookie is applied without
    // a wasted secondary GET; React Router handles navigation.
    return fetch(BASE + '/start', { method: 'POST', body, redirect: 'manual' })
  },

  submit: (answer: { optionIndex?: number; typedAnswer?: string }, currentIndex: number) => {
    const params: Record<string, string> = { current_index: String(currentIndex) }
    if (answer.optionIndex !== undefined) {
      params.selected_option_index = String(answer.optionIndex)
    }
    if (answer.typedAnswer !== undefined) {
      params.typed_answer = answer.typedAnswer
    }
    return json<AnswerRecord>('/submit_answer', {
      method: 'POST',
      body: new URLSearchParams(params),
    })
  },

  reset: () => json<{ status: string }>('/api/reset', { method: 'POST' }),
}
