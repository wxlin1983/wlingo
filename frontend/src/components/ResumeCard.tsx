import { Link } from 'react-router-dom'
import type { SessionInfo } from '../lib/types'

interface Props {
  session: SessionInfo
  className?: string
}

export default function ResumeCard({ session, className = '' }: Props) {
  const href = session.completed ? '/result' : `/quiz/${session.current_index ?? 0}`
  const label = session.completed ? 'See Results →' : 'Resume →'
  const progress = session.completed
    ? 'Quiz completed'
    : `Question ${(session.current_index ?? 0) + 1} of ${session.total_questions}`

  return (
    <div
      className={`flex items-center justify-between gap-4 bg-sky-50 border border-sky-200 rounded-xl px-4 py-3 ${className}`}
    >
      <div className="min-w-0">
        <p className="font-semibold text-sky-800 text-sm truncate">{session.topic}</p>
        <p className="text-sky-600 text-xs">{progress}</p>
      </div>
      <Link
        to={href}
        className="flex-shrink-0 text-sm font-semibold text-white bg-sky-500 hover:bg-sky-600 active:scale-95 px-4 py-2 rounded-lg transition-all"
      >
        {label}
      </Link>
    </div>
  )
}
