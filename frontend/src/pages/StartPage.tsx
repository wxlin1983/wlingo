import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../lib/api'
import type { Topic, SessionInfo, QuizType } from '../lib/types'
import ModeToggle from '../components/ModeToggle'
import ResumeCard from '../components/ResumeCard'
import PageShell from '../components/PageShell'
import Spinner from '../components/Spinner'
import TopicSection, { type SectionAccent } from '../components/TopicSection'

interface SectionDef {
  quizType: QuizType
  title: string
  icon: string
  description: string
  accent: SectionAccent
}

// Tailwind can only see complete literal class strings, so each accent is
// spelled out in full here rather than built from a color name.
const SECTIONS: SectionDef[] = [
  {
    quizType: 'multiple_choice',
    title: 'Multiple Choice',
    icon: '🔤',
    description: 'Pick the right translation',
    accent: {
      chipSelected: 'border-sky-500 bg-sky-50 text-sky-700',
      iconBg: 'bg-sky-100',
    },
  },
  {
    quizType: 'spelling',
    title: 'Spelling Practice',
    icon: '✏️',
    description: 'Type the reading of the word',
    accent: {
      chipSelected: 'border-emerald-500 bg-emerald-50 text-emerald-700',
      iconBg: 'bg-emerald-100',
    },
  },
  {
    quizType: 'translation',
    title: 'Translation Practice',
    icon: '🌐',
    description: 'Type the translation of the word',
    accent: {
      chipSelected: 'border-amber-500 bg-amber-50 text-amber-700',
      iconBg: 'bg-amber-100',
    },
  },
]

// Inline copy of the favicon mark (frontend/public/favicon.svg) so the header
// works without an extra asset request.
function Monogram() {
  return (
    <svg viewBox="0 0 100 100" aria-hidden="true" className="w-11 h-11 drop-shadow-md">
      <defs>
        <linearGradient id="wl-tile" x1="15%" y1="0%" x2="85%" y2="100%">
          <stop offset="0%" stopColor="#0c4a6e" />
          <stop offset="100%" stopColor="#062a43" />
        </linearGradient>
      </defs>
      <rect width="100" height="100" rx="22" fill="url(#wl-tile)" />
      <path
        d="M22 32 L38 70 L50 44 L62 70 L78 32"
        fill="none"
        stroke="#f0f9ff"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M44 44 L56 44 L50 32 Z" fill="#38bdf8" />
    </svg>
  )
}

const fadeUp = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
}

export default function StartPage() {
  const [topics, setTopics] = useState<Topic[]>([])
  const [topicsLoaded, setTopicsLoaded] = useState(false)
  const [selected, setSelected] = useState<Partial<Record<QuizType, string>>>({})
  const [mode, setMode] = useState<'adaptive' | 'random'>('adaptive')
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .topics()
      .then((t) => {
        setTopics(t)
        const initial: Partial<Record<QuizType, string>> = {}
        for (const s of SECTIONS) {
          const first = t.find((x) => x.quiz_type === s.quizType)
          if (first) initial[s.quizType] = first.id
        }
        setSelected(initial)
        setTopicsLoaded(true)
      })
      .catch(() => setError('Failed to load topics'))

    api
      .session()
      .then((s) => {
        if (s.active) setSession(s)
      })
      .catch(() => {})
  }, [])

  async function handleStart(topic?: string) {
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
      <div className="w-full max-w-md py-6">
        {/* Logo */}
        <motion.div {...fadeUp} className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Monogram />
            <h1 className="text-5xl font-extrabold text-green-500 tracking-tight">wlingo</h1>
          </div>
          <p className="text-gray-400 text-lg">Choose a topic and start learning!</p>
        </motion.div>

        {/* Resume banner */}
        {session && (
          <motion.div {...fadeUp} transition={{ delay: 0.05 }}>
            <ResumeCard session={session} className="mb-4" />
          </motion.div>
        )}

        {/* Mode selector — shared, applies to whichever section starts a quiz */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-lg p-5 mb-4"
        >
          <ModeToggle value={mode} onChange={setMode} />
        </motion.div>

        {!topicsLoaded && !error && (
          <div className="py-10 flex justify-center">
            <Spinner />
          </div>
        )}

        <div className="space-y-4">
          {SECTIONS.map((s, i) => (
            <motion.div key={s.quizType} {...fadeUp} transition={{ delay: 0.15 + i * 0.07 }}>
              <TopicSection
                title={s.title}
                icon={s.icon}
                description={s.description}
                accent={s.accent}
                topics={topics.filter((t) => t.quiz_type === s.quizType)}
                selectedTopic={selected[s.quizType] ?? ''}
                onSelectTopic={(id) => setSelected((prev) => ({ ...prev, [s.quizType]: id }))}
                onStart={() => handleStart(selected[s.quizType])}
                loading={loading}
              />
            </motion.div>
          ))}
        </div>

        {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
      </div>
    </PageShell>
  )
}
