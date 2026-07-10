import type { Topic } from '../lib/types'
import PrimaryButton from './PrimaryButton'

export interface SectionAccent {
  /** Complete class string for a selected topic chip */
  chipSelected: string
  /** Complete class string for the icon badge background */
  iconBg: string
}

interface Props {
  title: string
  icon: string
  description: string
  accent: SectionAccent
  topics: Topic[]
  selectedTopic: string
  onSelectTopic: (id: string) => void
  onStart: () => void
  loading: boolean
}

export default function TopicSection({
  title,
  icon,
  description,
  accent,
  topics,
  selectedTopic,
  onSelectTopic,
  onStart,
  loading,
}: Props) {
  if (topics.length === 0) return null

  return (
    <section className="bg-white rounded-2xl shadow-lg p-6 space-y-4">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0 ${accent.iconBg}`}
        >
          {icon}
        </span>
        <div>
          <h2 className="text-base font-bold text-gray-800 leading-tight">{title}</h2>
          <p className="text-xs text-gray-400">{description}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label={`${title} topics`}>
        {topics.map((t) => {
          const active = t.id === selectedTopic
          return (
            <button
              key={t.id}
              onClick={() => onSelectTopic(t.id)}
              aria-pressed={active}
              className={`px-3 py-2 rounded-xl border-2 text-sm font-semibold transition-colors ${
                active
                  ? accent.chipSelected
                  : 'border-gray-200 text-gray-600 hover:border-gray-300 bg-white'
              }`}
            >
              {t.name} <span className={active ? 'opacity-60' : 'text-gray-400'}>· {t.count}</span>
            </button>
          )
        })}
      </div>

      <PrimaryButton onClick={onStart} disabled={loading}>
        {loading ? 'Starting…' : 'Start Quiz ▶'}
      </PrimaryButton>
    </section>
  )
}
