export type OptionState = 'idle' | 'correct' | 'wrong' | 'correct-reveal' | 'disabled'

interface Props {
  label: string
  hotkey: number
  state: OptionState
  onClick: () => void
}

const stateClass: Record<OptionState, string> = {
  idle: 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100 hover:border-gray-300 cursor-pointer',
  correct: 'bg-green-50 border-green-500 text-green-800 cursor-default animate-pulse_correct',
  wrong: 'bg-red-50 border-red-400 text-red-800 cursor-default animate-shake',
  'correct-reveal': 'bg-green-50 border-green-400 text-green-700 cursor-default',
  disabled: 'bg-gray-50 border-gray-200 text-gray-400 cursor-default opacity-60',
}

export default function OptionButton({ label, hotkey, state, onClick }: Props) {
  return (
    <button
      onClick={state === 'idle' ? onClick : undefined}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-left font-medium transition-colors ${stateClass[state]}`}
    >
      <span className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-md border border-gray-300 bg-white text-xs font-bold text-gray-500">
        {hotkey}
      </span>
      <span>{label}</span>
    </button>
  )
}
