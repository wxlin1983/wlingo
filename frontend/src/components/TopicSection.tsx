import type { Topic } from '../lib/types'
import PrimaryButton from './PrimaryButton'

interface Props {
  title: string
  topics: Topic[]
  selectedTopic: string
  onSelectTopic: (id: string) => void
  onStart: () => void
  loading: boolean
}

export default function TopicSection({
  title,
  topics,
  selectedTopic,
  onSelectTopic,
  onStart,
  loading,
}: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 space-y-4">
      <h2 className="text-sm font-semibold text-gray-600">{title}</h2>
      <select
        value={selectedTopic}
        onChange={(e) => onSelectTopic(e.target.value)}
        disabled={topics.length === 0}
        className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:border-sky-400 focus:outline-none text-gray-700 bg-white disabled:opacity-50 transition-colors"
      >
        {topics.length === 0 && <option>Loading…</option>}
        {topics.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} ({t.count} words)
          </option>
        ))}
      </select>
      <PrimaryButton onClick={onStart} disabled={topics.length === 0 || loading}>
        {loading ? 'Starting…' : 'Start Quiz ▶'}
      </PrimaryButton>
    </div>
  )
}
