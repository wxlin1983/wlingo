import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ResultPage from './ResultPage'
import { api } from '../lib/api'
import type { QuizResult } from '../lib/types'

vi.mock('../lib/api', () => ({
  api: {
    result: vi.fn(),
    reset: vi.fn(),
  },
}))

const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

const RESULT: QuizResult = {
  correct_count: 1,
  total_questions: 2,
  score_percentage: 50,
  answers: [
    {
      word: 'hello',
      user_answer: '你好',
      correct_answer: '你好',
      is_correct: true,
      explanation: '',
    },
    {
      word: 'goodbye',
      user_answer: '你好',
      correct_answer: '再見',
      is_correct: false,
      explanation: 'Common greeting mix-up.',
    },
  ],
}

describe('ResultPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.result).mockResolvedValue(RESULT)
    vi.mocked(api.reset).mockResolvedValue({ status: 'success' })
  })

  it('shows the score and answer review, then resets on demand', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('1 of 2 correct')).toBeInTheDocument()
    expect(screen.getByText('hello')).toBeInTheDocument()
    expect(screen.getByText('Common greeting mix-up.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start new quiz/i }))

    expect(api.reset).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/')
  })

  it('redirects home if the result fails to load', async () => {
    vi.mocked(api.result).mockRejectedValue(new Error('no session'))

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/')
    })
  })
})
