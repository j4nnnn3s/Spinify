import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Connect from './pages/Connect'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <header className="border-b border-neutral-800 bg-neutral-900/80 backdrop-blur">
          <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-3">
              <img src="/logo.png" alt="Spinify" className="h-9 w-9 rounded-full object-cover" />
              <span className="font-semibold text-lg tracking-tight">Spinify</span>
            </Link>
            <nav className="flex gap-6 text-sm text-neutral-400">
              <Link to="/" className="hover:text-white transition-colors">Dashboard</Link>
              <Link to="/records" className="hover:text-white transition-colors">Records</Link>
              <Link to="/connect" className="hover:text-white transition-colors">Connect</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/records" element={<Records />} />
            <Route path="/connect" element={<Connect />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
