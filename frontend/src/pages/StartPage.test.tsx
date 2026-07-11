import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import StartPage from './StartPage'
import { api } from '../lib/api'

vi.mock('../lib/api', () => ({
  api: {
    topics: vi.fn(),
    session: vi.fn(),
    start: vi.fn(),
  },
}))

const navigateMock = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

function section(title: string) {
  const heading = screen.getByRole('heading', { name: title })
  return within(heading.closest('section')!)
}

function renderPage() {
  return render(
    <MemoryRouter>
      <StartPage />
    </MemoryRouter>,
  )
}

describe('StartPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.topics).mockResolvedValue([
      { id: 'English', name: 'English', count: 281, quiz_type: 'multiple_choice' },
      { id: 'Korean', name: 'Korean', count: 675, quiz_type: 'multiple_choice' },
      {
        id: 'Chinese_to_English',
        name: 'Chinese To English',
        count: 281,
        quiz_type: 'translation',
      },
      { id: 'Japanese_Kanji', name: 'Japanese Kanji', count: 99, quiz_type: 'spelling' },
    ])
    vi.mocked(api.session).mockResolvedValue({ active: false })
  })

  it('separates topics into Multiple Choice, Spelling, and Translation sections', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^English/ })).toBeInTheDocument()
    })

    const mc = section('Multiple Choice')
    expect(mc.getByRole('button', { name: /^English/ })).toBeInTheDocument()
    expect(mc.getByRole('button', { name: /Korean/ })).toBeInTheDocument()
    expect(mc.queryByRole('button', { name: /Chinese To English/ })).not.toBeInTheDocument()

    const spelling = section('Spelling Practice')
    expect(spelling.getByRole('button', { name: /Japanese Kanji/ })).toBeInTheDocument()
    expect(spelling.queryByRole('button', { name: /Chinese To English/ })).not.toBeInTheDocument()

    const translation = section('Translation Practice')
    expect(translation.getByRole('button', { name: /Chinese To English/ })).toBeInTheDocument()
    expect(translation.queryByRole('button', { name: /^English/ })).not.toBeInTheDocument()
  })

  it('hides a section that has no topics', async () => {
    vi.mocked(api.topics).mockResolvedValue([
      { id: 'English', name: 'English', count: 281, quiz_type: 'multiple_choice' },
    ])

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^English/ })).toBeInTheDocument()
    })

    expect(screen.queryByRole('heading', { name: 'Spelling Practice' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Translation Practice' })).not.toBeInTheDocument()
  })

  it('starts a multiple-choice quiz from the Multiple Choice section', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^English/ })).toBeInTheDocument()
    })

    await user.click(section('Multiple Choice').getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('English', 'adaptive')
      expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
    })
  })

  it('starts the quiz for a newly selected topic chip', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Korean/ })).toBeInTheDocument()
    })

    const mc = section('Multiple Choice')
    await user.click(mc.getByRole('button', { name: /Korean/ }))
    expect(mc.getByRole('button', { name: /Korean/ })).toHaveAttribute('aria-pressed', 'true')

    await user.click(mc.getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('Korean', 'adaptive')
    })
  })

  it('starts a spelling quiz from the Spelling Practice section', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Japanese Kanji/ })).toBeInTheDocument()
    })

    await user.click(section('Spelling Practice').getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('Japanese_Kanji', 'adaptive')
      expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
    })
  })

  it('starts a translation quiz from the Translation Practice section', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Chinese To English/ })).toBeInTheDocument()
    })

    await user.click(section('Translation Practice').getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('Chinese_to_English', 'adaptive')
      expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
    })
  })

  it('shows an error message instead of navigating when starting fails', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({
      type: 'default',
      ok: false,
      json: () => Promise.resolve({ detail: 'Unknown topic' }),
    } as unknown as Response)

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^English/ })).toBeInTheDocument()
    })

    await user.click(section('Multiple Choice').getByRole('button', { name: /start quiz/i }))

    expect(await screen.findByText('Unknown topic')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
