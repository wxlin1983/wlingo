import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import StartPage from './pages/StartPage'
import QuizPage from './pages/QuizPage'
import ResultPage from './pages/ResultPage'
import { ROOT_PATH } from './lib/env'

export default function App() {
  return (
    <BrowserRouter basename={ROOT_PATH}>
      <Routes>
        <Route path="/" element={<StartPage />} />
        <Route path="/quiz/:index" element={<QuizPage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
