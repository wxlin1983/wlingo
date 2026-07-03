import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { Topic, SessionInfo } from '../lib/types'
import ModeToggle from '../components/ModeToggle'
import ResumeCard from '../components/ResumeCard'

export default function StartPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedTopic, setSelectedTopic] = useState('')
  const [mode, setMode] = useState<'adaptive' | 'random'>('adaptive')
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.topics()
      .then(t => {
        setTopics(t)
        if (t.length > 0) setSelectedTopic(t[0].id)
      })
      .catch(() => setError('Failed to load topics'))

    api.session()
      .then(s => { if (s.active) setSession(s) })
      .catch(() => {})
  }, [])

  async function handleStart(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedTopic) return
    setLoading(true)
    setError('')
    try {
      const res = await api.start(selectedTopic, mode)
      // 302 → type:'opaqueredirect', status:0 → success
      // 400+ → type:'default', ok:false → error
      if (res.type === 'opaqueredirect' || res.ok) {
        navigate('/quiz/0')
      } else {
        const body = await res.json().catch(() => ({})) as { detail?: string }
        setError(body.detail ?? 'Failed to start quiz')
      }
    } catch {
      setError('Network error — is the server running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-6xl font-extrabold text-green-500 tracking-tight mb-2">
            wlingo
          </h1>
          <p className="text-gray-400 text-lg">Choose a topic and start learning!</p>
        </div>

        {/* Resume banner */}
        {session && (
          <ResumeCard session={session} className="mb-4" />
        )}

        {/* Main card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 space-y-6">
          {/* Topic selector */}
          <div>
            <label
              htmlFor="topic"
              className="block text-sm font-semibold text-gray-600 mb-2"
            >
              Vocabulary Set
            </label>
            <select
              id="topic"
              value={selectedTopic}
              onChange={e => setSelectedTopic(e.target.value)}
              disabled={topics.length === 0}
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-sky-400 focus:outline-none text-gray-700 bg-white disabled:opacity-50 transition-colors"
            >
              {topics.length === 0 && (
                <option>Loading…</option>
              )}
              {topics.map(t => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.count} words)
                </option>
              ))}
            </select>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </div>

          {/* Mode selector */}
          <ModeToggle value={mode} onChange={setMode} />

          {/* Start button */}
          <button
            onClick={handleStart}
            disabled={topics.length === 0 || loading}
            className="w-full py-4 bg-green-500 hover:bg-green-600 active:scale-[0.98] active:translate-y-0.5 text-white font-bold text-xl rounded-2xl shadow-[0_4px_0_#16a34a] active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-100"
          >
            {loading ? 'Starting…' : 'Start Quiz ▶'}
          </button>
        </div>
      </div>
    </div>
  )
}
