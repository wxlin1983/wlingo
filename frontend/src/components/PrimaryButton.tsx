import type { MouseEventHandler, ReactNode } from 'react'

interface Props {
  onClick: MouseEventHandler<HTMLButtonElement>
  disabled?: boolean
  children: ReactNode
}

export default function PrimaryButton({ onClick, disabled, children }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full py-4 bg-green-500 hover:bg-green-600 active:scale-[0.98] active:translate-y-0.5 text-white font-bold text-xl rounded-2xl shadow-[0_4px_0_#16a34a] active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-100"
    >
      {children}
    </button>
  )
}
