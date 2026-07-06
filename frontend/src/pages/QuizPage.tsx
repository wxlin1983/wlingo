import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../lib/api'
import type { Question, AnswerRecord } from '../lib/types'
import ProgressBar from '../components/ProgressBar'
import OptionButton, { type OptionState } from '../components/OptionButton'

const LANG_MAP: Record<string, string> = {
  English: 'en-US',
  Korean: 'ko-KR',
}

export default function QuizPage() {
  const { index: indexStr } = useParams<{ index: string }>()
  const index = parseInt(indexStr ?? '0', 10)
  const navigate = useNavigate()

  const [question, setQuestion] = useState<Question | null>(null)
  const [topic, setTopic] = useState('')
  const [result, setResult] = useState<AnswerRecord | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [speaking, setSpeaking] = useState(false)

  // Load session once to get topic (for TTS language)
  useEffect(() => {
    api
      .session()
      .then((s) => {
        if (!s.active) {
          navigate('/')
          return
        }
        setTopic(s.topic ?? '')
      })
      .catch(() => navigate('/'))
  }, [navigate])

  // Load question whenever index changes
  useEffect(() => {
    if (!Number.isInteger(index) || index < 0) {
      navigate('/')
      return
    }
    setQuestion(null)
    setResult(null)
    api
      .question(index)
      .then((q) => {
        setQuestion(q)
        if (q.answer_record) setResult(q.answer_record)
      })
      .catch(() => navigate('/'))
  }, [index, navigate])

  const speak = useCallback(() => {
    if (!question || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(question.word)
    if (topic in LANG_MAP) utt.lang = LANG_MAP[topic]
    utt.rate = 0.9
    setSpeaking(true)
    utt.onend = () => setSpeaking(false)
    window.speechSynthesis.speak(utt)
  }, [question, topic])

  const handleSubmit = useCallback(
    async (optionIndex: number) => {
      if (!question || result || submitting) return
      setSubmitting(true)
      try {
        const r = await api.submit(optionIndex, index)
        setResult(r)
      } catch {
        // ignore
      } finally {
        setSubmitting(false)
      }
    },
    [question, result, submitting, index],
  )

  const goNext = useCallback(() => {
    if (!question) return
    if (index + 1 < question.total_questions) navigate(`/quiz/${index + 1}`)
    else navigate('/result')
  }, [question, index, navigate])

  const cancel = useCallback(() => {
    api
      .reset()
      .catch(() => {})
      .finally(() => navigate('/'))
  }, [navigate])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (['1', '2', '3', '4'].includes(e.key) && !result && question) {
        const i = parseInt(e.key) - 1
        if (i < question.options.length) handleSubmit(i)
      }
      if (e.key === 'Enter' && result) goNext()
      if (e.key.toLowerCase() === 's') speak()
      if (e.key === 'Escape') cancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [result, question, handleSubmit, goNext, speak, cancel])

  function optionState(i: number): OptionState {
    if (!result || !question) return submitting ? 'disabled' : 'idle'
    const opt = question.options[i]
    if (opt === result.correct_answer && opt === result.user_answer) return 'correct'
    if (opt === result.correct_answer) return 'correct-reveal'
    if (opt === result.user_answer) return 'wrong'
    return 'disabled'
  }

  if (!question) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const answered = result ? index + 1 : index

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-5">
          <div className="flex justify-between text-sm text-gray-400 mb-1.5">
            <span>
              Question {index + 1} / {question.total_questions}
            </span>
            <span>{Math.round((answered / question.total_questions) * 100)}%</span>
          </div>
          <ProgressBar current={answered} total={question.total_questions} />
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Word + Listen */}
          <div className="text-center mb-8">
            <p className="text-4xl font-bold text-gray-800 mb-4 leading-tight">{question.word}</p>
            <button
              onClick={speak}
              className={`inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors ${
                speaking
                  ? 'border-sky-400 text-sky-600 bg-sky-50'
                  : 'border-gray-200 text-gray-400 hover:border-gray-300 hover:text-gray-600'
              }`}
            >
              🔊 Listen
            </button>
          </div>

          {/* Options */}
          <div className="space-y-3 mb-6">
            {question.options.map((opt, i) => (
              <OptionButton
                key={i}
                label={opt}
                hotkey={i + 1}
                state={optionState(i)}
                onClick={() => handleSubmit(i)}
              />
            ))}
          </div>

          {/* Feedback */}
          <AnimatePresence>
            {result && (
              <motion.p
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`text-center font-semibold mb-5 ${
                  result.is_correct ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {result.is_correct ? '✓ Correct!' : `✗ The answer is "${result.correct_answer}"`}
              </motion.p>
            )}
          </AnimatePresence>

          {/* Nav */}
          <div className="flex justify-between items-center">
            <button
              onClick={cancel}
              className="px-4 py-2 text-sm text-gray-400 border border-gray-200 rounded-lg hover:bg-red-50 hover:border-red-300 hover:text-red-500 transition-colors"
            >
              ✕ Cancel
            </button>

            <AnimatePresence>
              {result && (
                <motion.button
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  onClick={goNext}
                  className="px-6 py-2 bg-sky-500 hover:bg-sky-600 text-white font-semibold rounded-lg transition-colors"
                >
                  {index + 1 < question.total_questions ? 'Next →' : 'See Results 🎉'}
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Keyboard hint */}
        <p className="text-center text-xs text-gray-400 mt-4">
          <strong>1–4</strong> select · <strong>Enter</strong> next · <strong>S</strong> listen ·{' '}
          <strong>Esc</strong> cancel
        </p>
      </div>
    </div>
  )
}
