import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../lib/api'
import type { QuizResult } from '../lib/types'
import ScoreRing from '../components/ScoreRing'

export default function ResultPage() {
  const [result, setResult] = useState<QuizResult | null>(null)
  const [resetting, setResetting] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.result()
      .then(setResult)
      .catch(() => navigate('/'))
  }, [navigate])

  async function handleReset() {
    setResetting(true)
    try {
      await api.reset()
    } finally {
      navigate('/')
    }
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">

        {/* Score card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg p-8 mb-6"
        >
          <h1 className="text-2xl font-bold text-center text-gray-800 mb-8">
            Quiz Results
          </h1>

          <div className="flex flex-col items-center mb-8">
            <ScoreRing score={result.score_percentage} />
            <p className="text-gray-500 mt-3 text-sm">
              {result.correct_count} of {result.total_questions} correct
            </p>
          </div>

          <button
            onClick={handleReset}
            disabled={resetting}
            className="w-full py-4 bg-green-500 hover:bg-green-600 active:scale-[0.98] active:translate-y-0.5 text-white font-bold text-lg rounded-2xl shadow-[0_4px_0_#16a34a] active:shadow-none disabled:opacity-50 transition-all duration-100"
          >
            {resetting ? 'Resetting…' : 'Start New Quiz 🔄'}
          </button>
        </motion.div>

        {/* Answer review */}
        <h2 className="font-semibold text-gray-600 mb-3 px-1">Answer Review</h2>
        <div className="space-y-3">
          {result.answers.map((ans, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex items-start gap-3"
            >
              <span
                className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  ans.is_correct
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-600'
                }`}
              >
                {ans.is_correct ? '✓' : '✗'}
              </span>
              <div className="min-w-0">
                <p className="font-semibold text-gray-800">{ans.word}</p>
                {!ans.is_correct && (
                  <p className="text-sm text-red-500 truncate">
                    Your answer: {ans.user_answer}
                  </p>
                )}
                <p className="text-sm text-green-600 truncate">
                  Correct: {ans.correct_answer}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}
