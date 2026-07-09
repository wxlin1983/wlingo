export type QuizType = 'multiple_choice' | 'spelling'

export interface Topic {
  id: string
  name: string
  count: number
  quiz_type: QuizType
}

export interface AnswerRecord {
  word: string
  user_answer: string
  correct_answer: string
  is_correct: boolean
  explanation: string
}

export interface Question {
  word: string
  options: string[]
  quiz_type: QuizType
  current_index: number
  total_questions: number
  answer_record: AnswerRecord | null
}

export interface SessionInfo {
  active: boolean
  completed?: boolean
  topic?: string
  mode?: string
  quiz_type?: QuizType
  current_index?: number
  total_questions?: number
}

export interface QuizResult {
  correct_count: number
  total_questions: number
  score_percentage: number
  answers: AnswerRecord[]
}
