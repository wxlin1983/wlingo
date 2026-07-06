import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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

describe('StartPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.topics).mockResolvedValue([
      { id: 'English', name: 'English', count: 281 },
      { id: 'Korean', name: 'Korean', count: 675 },
    ])
    vi.mocked(api.session).mockResolvedValue({ active: false })
  })

  it('loads topics and starts a quiz on submit', async () => {
    const user = userEvent.setup()
    vi.mocked(api.start).mockResolvedValue({ type: 'opaqueredirect' } as Response)

    render(
      <MemoryRouter>
        <StartPage />
      </MemoryRouter>,
    )

    // The select starts on "Loading…" and is populated once topics resolve.
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /English/ })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /start quiz/i }))

    await waitFor(() => {
      expect(api.start).toHaveBeenCalledWith('English', 'adaptive')
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

    await user.click(screen.getByRole('button', { name: /start quiz/i }))

    expect(await screen.findByText('Unknown topic')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })
})
