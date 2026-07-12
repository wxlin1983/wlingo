import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ResultPage from './ResultPage'
import { api } from '../lib/api'
import type { QuizResult, WordStat } from '../lib/types'

vi.mock('../lib/api', () => ({
  api: {
    result: vi.fn(),
    reset: vi.fn(),
    start: vi.fn(),
    wordStats: vi.fn(),
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
  topic: 'English',
  mode: 'adaptive',
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
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)
    vi.mocked(api.wordStats).mockResolvedValue([])
  })

  it('shows wrong answers up front with correct ones collapsed, then resets on demand', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('1 of 2 correct')).toBeInTheDocument()
    // The wrong answer and its explanation are visible immediately…
    expect(screen.getByText('goodbye')).toBeInTheDocument()
    expect(screen.getByText('Common greeting mix-up.')).toBeInTheDocument()
    // …but the correct answer is tucked away until the accordion is opened.
    expect(screen.queryByText('hello')).not.toBeInTheDocument()

    const accordion = screen.getByRole('button', { name: /correct answers \(1\)/i })
    expect(accordion).toHaveAttribute('aria-expanded', 'false')
    await user.click(accordion)
    expect(accordion).toHaveAttribute('aria-expanded', 'true')
    expect(await screen.findByText('hello')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /choose different topic/i }))

    expect(api.reset).toHaveBeenCalled()
    expect(navigateMock).toHaveBeenCalledWith('/')
  })

  it('omits the accordion when every answer is wrong', async () => {
    vi.mocked(api.result).mockResolvedValue({
      correct_count: 0,
      total_questions: 1,
      score_percentage: 0,
      topic: 'English',
      mode: 'adaptive',
      answers: [RESULT.answers[1]],
    })

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('goodbye')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /correct answers/i })).not.toBeInTheDocument()
  })

  it('shows a perfect-score message when every answer is correct', async () => {
    vi.mocked(api.result).mockResolvedValue({
      correct_count: 1,
      total_questions: 1,
      score_percentage: 100,
      topic: 'English',
      mode: 'adaptive',
      answers: [RESULT.answers[0]],
    })

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/nothing to review/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /correct answers \(1\)/i })).toBeInTheDocument()
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

  it('restarts the same quiz topic/mode when the retry button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /retry quiz/i }))

    expect(api.start).toHaveBeenCalledWith('English', 'adaptive')
    expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
  })

  it('restarts the same quiz when the R key is pressed', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await screen.findByText('1 of 2 correct')
    await user.keyboard('r')

    expect(api.start).toHaveBeenCalledWith('English', 'adaptive')
    expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
  })

  it('shows an error instead of navigating when restart fails', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({
      type: 'default',
      ok: false,
      json: () => Promise.resolve({}),
    } as unknown as Response)

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /retry quiz/i }))

    expect(await screen.findByText(/failed to restart quiz/i)).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalledWith('/quiz/0')
  })

  it('lazy-loads and renders the word accuracy table, worst first, on toggle', async () => {
    const user = userEvent.setup()
    const stats: WordStat[] = [
      { word: 'worst', correct: 0, total: 4, accuracy_percentage: 0 },
      { word: 'best', correct: 5, total: 5, accuracy_percentage: 100 },
    ]
    vi.mocked(api.wordStats).mockResolvedValue(stats)

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    const toggle = await screen.findByRole('button', { name: /word accuracy/i })
    expect(api.wordStats).not.toHaveBeenCalled()
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await user.click(toggle)

    expect(api.wordStats).toHaveBeenCalledWith('English')
    expect(toggle).toHaveAttribute('aria-expanded', 'true')

    const rows = await screen.findAllByRole('row')
    // rows[0] is the header row
    expect(rows[1]).toHaveTextContent('worst')
    expect(rows[1]).toHaveTextContent('0/4')
    expect(rows[1]).toHaveTextContent('0%')
    expect(rows[2]).toHaveTextContent('best')
    expect(rows[2]).toHaveTextContent('100%')

    // Collapsing and reopening must not trigger a second fetch.
    await user.click(toggle)
    await user.click(toggle)
    expect(api.wordStats).toHaveBeenCalledTimes(1)
  })

  it('shows a message when there is no word history yet', async () => {
    const user = userEvent.setup()
    vi.mocked(api.wordStats).mockResolvedValue([])

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /word accuracy/i }))

    expect(await screen.findByText(/no history yet/i)).toBeInTheDocument()
  })

  it('shows an error if word accuracy fails to load', async () => {
    const user = userEvent.setup()
    vi.mocked(api.wordStats).mockRejectedValue(new Error('network error'))

    render(
      <MemoryRouter>
        <ResultPage />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /word accuracy/i }))

    expect(await screen.findByText(/failed to load word accuracy/i)).toBeInTheDocument()
  })
})
