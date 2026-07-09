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
  return within(heading.closest('div')!)
}

describe('StartPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.topics).mockResolvedValue([
      { id: 'English', name: 'English', count: 281, quiz_type: 'multiple_choice' },
      { id: 'Korean', name: 'Korean', count: 675, quiz_type: 'multiple_choice' },
      { id: 'Chinese_Spelling', name: 'Chinese Spelling', count: 281, quiz_type: 'spelling' },
      { id: 'Japanese_Kanji', name: 'Japanese Kanji', count: 99, quiz_type: 'spelling' },
    ])
    vi.mocked(api.session).mockResolvedValue({ active: false })
  })

  it('separates topics into Multiple Choice and Spelling Practice sections', async () => {
    render(
      <MemoryRouter>
        <StartPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /English/ })).toBeInTheDocument()
    })

    const mc = section('Multiple Choice')
    expect(mc.getByRole('option', { name: /English/ })).toBeInTheDocument()
    expect(mc.getByRole('option', { name: /Korean/ })).toBeInTheDocument()
    expect(mc.queryByRole('option', { name: /Chinese Spelling/ })).not.toBeInTheDocument()

    const spelling = section('Spelling Practice')
    expect(spelling.getByRole('option', { name: /Chinese Spelling/ })).toBeInTheDocument()
    expect(spelling.getByRole('option', { name: /Japanese Kanji/ })).toBeInTheDocument()
    expect(spelling.queryByRole('option', { name: /^English/ })).not.toBeInTheDocument()
  })

  it('starts a multiple-choice quiz from the Multiple Choice section', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    render(
      <MemoryRouter>
        <StartPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /English/ })).toBeInTheDocument()
    })

    await user.click(section('Multiple Choice').getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('English', 'adaptive')
      expect(navigateMock).toHaveBeenCalledWith('/quiz/0')
    })
  })

  it('starts a spelling quiz from the Spelling Practice section', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    render(
      <MemoryRouter>
        <StartPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Chinese Spelling/ })).toBeInTheDocument()
    })

    await user.click(section('Spelling Practice').getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('Chinese_Spelling', 'adaptive')
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

    render(
      <MemoryRouter>
        <StartPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /English/ })).toBeInTheDocument()
    })

    await user.click(section('Multiple Choice').getByRole('button', { name: /start quiz/i }))

    expect(await screen.findByText('Unknown topic')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
