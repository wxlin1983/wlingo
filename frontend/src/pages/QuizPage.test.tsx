import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import QuizPage from './QuizPage'
import { api } from '../lib/api'
import type { Question } from '../lib/types'

vi.mock('../lib/api', () => ({
  api: {
    session: vi.fn(),
    question: vi.fn(),
    submit: vi.fn(),
    reset: vi.fn(),
  },
}))

const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

const QUESTION: Question = {
  word: 'hello',
  options: ['你好', '再見', '謝謝', '對不起'],
  current_index: 0,
  total_questions: 5,
  answer_record: null,
}

function renderAtIndex(index: string) {
  return render(
    <MemoryRouter initialEntries={[`/quiz/${index}`]}>
      <Routes>
        <Route path="/quiz/:index" element={<QuizPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('QuizPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.session).mockResolvedValue({ active: true, topic: 'English' })
    vi.mocked(api.question).mockResolvedValue(QUESTION)
  })

  it('loads the question and submits the selected answer', async () => {
    const user = userEvent.setup()
    vi.mocked(api.submit).mockResolvedValue({
      word: 'hello',
      user_answer: '你好',
      correct_answer: '你好',
      is_correct: true,
      explanation: '',
    })

    renderAtIndex('0')

    expect(await screen.findByText('hello')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /你好/ }))

    expect(api.submit).toHaveBeenCalledWith(0, 0)
    expect(await screen.findByText('✓ Correct!')).toBeInTheDocument()
  })

  it('redirects home for a non-numeric route index instead of calling the API', async () => {
    renderAtIndex('not-a-number')

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith('/')
    })
    expect(api.question).not.toHaveBeenCalled()
  })
})
