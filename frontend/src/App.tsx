import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import LearningSession from './pages/LearningSession'
import Dashboard from './pages/Dashboard'
import SessionReport from './pages/SessionReport'

function Nav() {
  const loc = useLocation()
  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`text-sm px-3 py-1.5 rounded-lg transition ${
        loc.pathname === to
          ? 'bg-gray-700 text-white'
          : 'text-gray-400 hover:text-white hover:bg-gray-800'
      }`}
    >
      {label}
    </Link>
  )
  return (
    <nav className="border-b border-gray-800 bg-gray-950 px-6 py-3 flex items-center gap-2">
      <span className="text-white font-bold mr-4">🎓 Learning Analytics</span>
      {link('/', 'Học ngay')}
      {link('/dashboard', 'Dashboard')}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Nav />
        <Routes>
          <Route path="/" element={<LearningSession />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/report/:sessionId" element={<SessionReport />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
