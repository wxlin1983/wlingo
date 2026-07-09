import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { Topic, SessionInfo } from '../lib/types'
import ModeToggle from '../components/ModeToggle'
import ResumeCard from '../components/ResumeCard'
import PageShell from '../components/PageShell'
import TopicSection from '../components/TopicSection'

export default function StartPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [selectedMcTopic, setSelectedMcTopic] = useState('')
  const [selectedSpellingTopic, setSelectedSpellingTopic] = useState('')
  const [mode, setMode] = useState<'adaptive' | 'random'>('adaptive')
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const mcTopics = topics.filter((t) => t.quiz_type === 'multiple_choice')
  const spellingTopics = topics.filter((t) => t.quiz_type === 'spelling')

  useEffect(() => {
    api
      .topics()
      .then((t) => {
        setTopics(t)
        const mc = t.filter((x) => x.quiz_type === 'multiple_choice')
        const spelling = t.filter((x) => x.quiz_type === 'spelling')
        if (mc.length > 0) setSelectedMcTopic(mc[0].id)
        if (spelling.length > 0) setSelectedSpellingTopic(spelling[0].id)
      })
      .catch(() => setError('Failed to load topics'))

    api
      .session()
      .then((s) => {
        if (s.active) setSession(s)
      })
      .catch(() => {})
  }, [])

  async function handleStart(topic: string) {
    if (!topic) return
    setLoading(true)
    setError('')
    try {
      const res = await api.start(topic, mode)
      // 302 → type:'opaqueredirect', status:0 → success
      // 400+ → type:'default', ok:false → error
      if (res.type === 'opaqueredirect' || res.ok) {
        navigate('/quiz/0')
      } else {
        const body = (await res.json().catch(() => ({}))) as { detail?: string }
        setError(body.detail ?? 'Failed to start quiz')
      }
    } catch {
      setError('Network error — is the server running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <PageShell>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-6xl font-extrabold text-green-500 tracking-tight mb-2">wlingo</h1>
          <p className="text-gray-400 text-lg">Choose a topic and start learning!</p>
        </div>

        {/* Resume banner */}
        {session && <ResumeCard session={session} className="mb-4" />}

        {/* Mode selector — shared, applies to whichever section starts a quiz */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-4">
          <ModeToggle value={mode} onChange={setMode} />
        </div>

        <div className="space-y-4">
          <TopicSection
            title="Multiple Choice"
            topics={mcTopics}
            selectedTopic={selectedMcTopic}
            onSelectTopic={setSelectedMcTopic}
            onStart={() => handleStart(selectedMcTopic)}
            loading={loading}
          />
          <TopicSection
            title="Spelling Practice"
            topics={spellingTopics}
            selectedTopic={selectedSpellingTopic}
            onSelectTopic={setSelectedSpellingTopic}
            onStart={() => handleStart(selectedSpellingTopic)}
            loading={loading}
          />
        </div>

        {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
      </div>
    </PageShell>
  )
}
