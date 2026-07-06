import type { Topic, Question, AnswerRecord, SessionInfo, QuizResult } from './types'

const BASE = import.meta.env.VITE_ROOT_PATH || ''

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

  start: (topic: string, mode: string): Promise<Response> => {
    const body = new URLSearchParams({ topic, mode })
    // Use redirect:'manual' so the 302→session cookie is applied without
    // a wasted secondary GET; React Router handles navigation.
    return fetch(BASE + '/start', { method: 'POST', body, redirect: 'manual' })
  },

  submit: (selectedOptionIndex: number, currentIndex: number) =>
    json<AnswerRecord>('/submit_answer', {
      method: 'POST',
      body: new URLSearchParams({
        selected_option_index: String(selectedOptionIndex),
        current_index: String(currentIndex),
      }),
    }),

  reset: () => json<{ status: string }>('/api/reset', { method: 'POST' }),
}
