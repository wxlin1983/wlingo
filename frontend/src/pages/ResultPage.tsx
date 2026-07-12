import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/api'
import type { QuizResult, AnswerRecord, WordStat } from '../lib/types'
import ScoreRing from '../components/ScoreRing'
import PageShell from '../components/PageShell'
import Spinner from '../components/Spinner'
import PrimaryButton from '../components/PrimaryButton'

function AnswerCard({ ans, delay }: { ans: AnswerRecord; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-start gap-3"
    >
      <span
        className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
          ans.is_correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
        }`}
      >
        {ans.is_correct ? '✓' : '✗'}
      </span>
      <div className="min-w-0">
        <p className="font-semibold text-gray-800">{ans.word}</p>
        {!ans.is_correct && (
          <p className="text-sm text-red-500 truncate">Your answer: {ans.user_answer}</p>
        )}
        <p className="text-sm text-green-600 truncate">Correct: {ans.correct_answer}</p>
        {!ans.is_correct && ans.explanation && (
          <p className="text-sm text-gray-500 mt-1 italic">{ans.explanation}</p>
        )}
      </div>
    </motion.div>
  )
}

export default function ResultPage() {
  const [result, setResult] = useState<QuizResult | null>(null)
  const [resetting, setResetting] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [restartError, setRestartError] = useState('')
  const [showCorrect, setShowCorrect] = useState(false)
  const [wordStats, setWordStats] = useState<WordStat[] | null>(null)
  const [wordStatsLoading, setWordStatsLoading] = useState(false)
  const [wordStatsError, setWordStatsError] = useState('')
  const [showWordStats, setShowWordStats] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .result()
      .then(setResult)
      .catch(() => navigate('/'))
  }, [navigate])

  async function handleReset() {
    setResetting(true)
    try {
      await api.reset()
    } catch {
      // best-effort: the session will also expire via its own TTL
    } finally {
      navigate('/')
    }
  }

  const handleRestart = useCallback(async () => {
    if (!result || restarting) return
    setRestarting(true)
    setRestartError('')
    try {
      const res = await api.start(result.topic, result.mode)
      if (res.type === 'opaqueredirect' || res.ok) {
        navigate('/quiz/0')
      } else {
        setRestartError('Failed to restart quiz')
      }
    } catch {
      setRestartError('Network error — is the server running?')
    } finally {
      setRestarting(false)
    }
  }, [result, restarting, navigate])

  async function toggleWordStats() {
    if (!result) return
    const next = !showWordStats
    setShowWordStats(next)
    if (next && wordStats === null && !wordStatsLoading) {
      setWordStatsLoading(true)
      setWordStatsError('')
      try {
        setWordStats(await api.wordStats(result.topic))
      } catch {
        setWordStatsError('Failed to load word accuracy')
      } finally {
        setWordStatsLoading(false)
      }
    }
  }

  // 'R' restarts the same quiz -- the only hotkey on this page today.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'r') handleRestart()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleRestart])

  if (!result) {
    return (
      <PageShell>
        <Spinner />
      </PageShell>
    )
  }

  const wrong = result.answers.filter((a) => !a.is_correct)
  const correct = result.answers.filter((a) => a.is_correct)

  return (
    <PageShell>
      <div className="w-full max-w-lg">
        {/* Score card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg p-8 mb-6"
        >
          <h1 className="text-2xl font-bold text-center text-gray-800 mb-8">Quiz Results</h1>

          <div className="flex flex-col items-center mb-8">
            <ScoreRing score={result.score_percentage} />
            <p className="text-gray-500 mt-3 text-sm">
              {result.correct_count} of {result.total_questions} correct
            </p>
          </div>

          <PrimaryButton onClick={handleRestart} disabled={restarting || resetting}>
            {restarting ? 'Starting…' : 'Retry Quiz ↻'}
          </PrimaryButton>
          <p className="text-center text-xs text-gray-400 mt-2">
            press <strong>R</strong> to retry
          </p>
          {restartError && <p className="text-red-500 text-sm text-center mt-2">{restartError}</p>}

          <button
            onClick={handleReset}
            disabled={resetting || restarting}
            className="w-full mt-4 text-sm text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
          >
            {resetting ? 'Resetting…' : 'Choose Different Topic'}
          </button>
        </motion.div>

        {/* Word accuracy across every attempt at this topic, worst first */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden mb-6">
          <button
            onClick={toggleWordStats}
            aria-expanded={showWordStats}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <span>📊 Word Accuracy (All-Time)</span>
            <span
              aria-hidden="true"
              className={`text-gray-400 transition-transform duration-200 ${
                showWordStats ? 'rotate-90' : ''
              }`}
            >
              ▸
            </span>
          </button>
          <AnimatePresence initial={false}>
            {showWordStats && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="px-4 pb-4">
                  {wordStatsLoading ? (
                    <div className="flex justify-center py-4">
                      <Spinner />
                    </div>
                  ) : wordStatsError ? (
                    <p className="text-red-500 text-sm text-center py-2">{wordStatsError}</p>
                  ) : wordStats && wordStats.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-2">
                      No history yet for this topic — keep practicing to build it up.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-gray-400 border-b border-gray-100">
                            <th className="py-2 font-medium">Word</th>
                            <th className="py-2 font-medium text-right">Correct/Total</th>
                            <th className="py-2 font-medium text-right">Accuracy</th>
                          </tr>
                        </thead>
                        <tbody>
                          {wordStats?.map((stat) => (
                            <tr key={stat.word} className="border-b border-gray-50 last:border-0">
                              <td className="py-2 text-gray-800">{stat.word}</td>
                              <td className="py-2 text-right text-gray-500">
                                {stat.correct}/{stat.total}
                              </td>
                              <td
                                className={`py-2 text-right font-semibold ${
                                  stat.accuracy_percentage >= 70 ? 'text-green-600' : 'text-red-600'
                                }`}
                              >
                                {stat.accuracy_percentage}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Answer review — wrong answers first, they're what needs studying */}
        <h2 className="font-semibold text-gray-600 mb-3 px-1">Answer Review</h2>
        <div className="space-y-3">
          {wrong.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-sm text-gray-500 bg-white rounded-xl border border-gray-100 shadow-sm p-4"
            >
              Perfect score — nothing to review 🎉
            </motion.p>
          ) : (
            wrong.map((ans, i) => (
              <AnswerCard key={`${ans.word}-${i}`} ans={ans} delay={i * 0.04} />
            ))
          )}

          {/* Correct answers collapsed into an accordion */}
          {correct.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <button
                onClick={() => setShowCorrect((v) => !v)}
                aria-expanded={showCorrect}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
              >
                <span>
                  <span className="text-green-600">✓</span> Correct answers ({correct.length})
                </span>
                <span
                  aria-hidden="true"
                  className={`text-gray-400 transition-transform duration-200 ${
                    showCorrect ? 'rotate-90' : ''
                  }`}
                >
                  ▸
                </span>
              </button>
              <AnimatePresence initial={false}>
                {showCorrect && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="px-3 pb-3 space-y-3">
                      {correct.map((ans, i) => (
                        <AnswerCard key={`${ans.word}-${i}`} ans={ans} delay={i * 0.03} />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}
