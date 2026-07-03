import { useEffect, useState } from 'react'

interface Props {
  score: number // 0–100
}

const r = 54
const circumference = 2 * Math.PI * r // ≈ 339.3

function ringColor(score: number) {
  if (score >= 80) return '#22c55e' // green-500
  if (score >= 50) return '#f59e0b' // amber-500
  return '#ef4444'                   // red-500
}

export default function ScoreRing({ score }: Props) {
  const [offset, setOffset] = useState(circumference)

  useEffect(() => {
    // Defer one frame so the CSS transition fires
    const id = requestAnimationFrame(() => {
      setOffset(circumference * (1 - score / 100))
    })
    return () => cancelAnimationFrame(id)
  }, [score])

  return (
    <div className="relative w-40 h-40 flex items-center justify-center">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={ringColor(score)}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(0.4,0,0.2,1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-gray-800">{score}%</span>
      </div>
    </div>
  )
}
