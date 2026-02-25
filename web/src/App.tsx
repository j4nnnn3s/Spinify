import { Toaster } from 'react-hot-toast'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Settings from './pages/Settings'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgb(38 38 38)',
            color: 'rgb(229 229 229)',
            border: '1px solid rgb(64 64 64)',
          },
          error: { style: { border: '1px solid rgb(127 29 29)' } },
          success: { style: { border: '1px solid rgb(22 101 52)' } },
        }}
      />
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
              <Link to="/settings" className="hover:text-white transition-colors">Settings</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/records" element={<Records />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
