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
  quiz_type: 'multiple_choice',
  romaji_input: false,
  hangul_input: false,
  current_index: 0,
  total_questions: 5,
  answer_record: null,
}

const SPELLING_QUESTION: Question = {
  word: '你好',
  options: [],
  quiz_type: 'spelling',
  romaji_input: false,
  hangul_input: false,
  current_index: 0,
  total_questions: 5,
  answer_record: null,
}

const KANA_SPELLING_QUESTION: Question = {
  word: '漢字',
  options: [],
  quiz_type: 'spelling',
  romaji_input: true,
  hangul_input: false,
  current_index: 0,
  total_questions: 5,
  answer_record: null,
}

const HANGUL_TRANSLATION_QUESTION: Question = {
  word: 'こんにちは',
  options: [],
  quiz_type: 'translation',
  romaji_input: false,
  hangul_input: true,
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

    expect(api.submit).toHaveBeenCalledWith({ optionIndex: 0 }, 0)
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

describe('QuizPage spelling mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.session).mockResolvedValue({ active: true, topic: 'Japanese_Kanji' })
    vi.mocked(api.question).mockResolvedValue(SPELLING_QUESTION)
  })

  it('renders a text input instead of option buttons', async () => {
    renderAtIndex('0')
    expect(await screen.findByText('你好')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/type your answer/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^submit$/i })).toBeInTheDocument()
  })

  it('submits the typed answer and shows feedback', async () => {
    const user = userEvent.setup()
    vi.mocked(api.submit).mockResolvedValue({
      word: '你好',
      user_answer: 'hello',
      correct_answer: 'hello',
      is_correct: true,
      explanation: '',
    })

    renderAtIndex('0')
    await screen.findByText('你好')

    const input = screen.getByPlaceholderText(/type your answer/i)
    await user.type(input, 'hello{Enter}')

    expect(api.submit).toHaveBeenCalledWith({ typedAnswer: 'hello' }, 0)
    expect(await screen.findByText('✓ Correct!')).toBeInTheDocument()
  })

  it('does not trigger option-selection or TTS while typing digits/s', async () => {
    const user = userEvent.setup()
    const speakSpy = vi.fn()
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak: speakSpy })

    renderAtIndex('0')
    await screen.findByText('你好')

    const input = screen.getByPlaceholderText(/type your answer/i)
    await user.type(input, '1s2')

    expect(input).toHaveValue('1s2')
    expect(api.submit).not.toHaveBeenCalled()
    expect(speakSpy).not.toHaveBeenCalled()

    vi.unstubAllGlobals()
  })
})

describe('QuizPage translation mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.session).mockResolvedValue({ active: true, topic: 'Chinese_to_English' })
    vi.mocked(api.question).mockResolvedValue({
      word: '你好',
      options: [],
      quiz_type: 'translation',
      romaji_input: false,
      hangul_input: false,
      current_index: 0,
      total_questions: 5,
      answer_record: null,
    })
  })

  it('renders the typed-answer input like spelling mode', async () => {
    renderAtIndex('0')
    expect(await screen.findByText('你好')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/type your answer/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^submit$/i })).toBeInTheDocument()
  })
})

describe('QuizPage kana spelling mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.session).mockResolvedValue({ active: true, topic: 'Japanese_Kanji' })
    vi.mocked(api.question).mockResolvedValue(KANA_SPELLING_QUESTION)
  })

  it('renders a romaji-input placeholder for kana spelling topics', async () => {
    renderAtIndex('0')
    expect(await screen.findByText('漢字')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/type romaji/i)).toBeInTheDocument()
  })
})

describe('QuizPage hangul translation mode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.session).mockResolvedValue({ active: true, topic: 'Japanese_to_Korean' })
    vi.mocked(api.question).mockResolvedValue(HANGUL_TRANSLATION_QUESTION)
  })

  it('renders a 2-beolsik input placeholder for hangul translation topics', async () => {
    renderAtIndex('0')
    expect(await screen.findByText('こんにちは')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/english keyboard/i)).toBeInTheDocument()
  })
})
