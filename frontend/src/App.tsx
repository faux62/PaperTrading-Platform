import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Trading from './pages/Trading'
import Markets from './pages/Markets'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Login from './pages/Login'

function App() {
  return (
    <div className="min-h-screen bg-gray-900">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/trading" element={<Trading />} />
        <Route path="/markets" element={<Markets />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </div>
  )
}

export default App
