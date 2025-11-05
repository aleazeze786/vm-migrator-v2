import React, { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { API, http } from './api'

function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin')
  const [error, setError] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await http.post(`${API}/token`, { username, password })
      localStorage.setItem('token', res.data.access_token)
      onLogin()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed')
    }
  }
  return (
    <div className="min-h-screen bg-[var(--body-bg)] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-semibold tracking-tight text-[var(--text-primary)]">VM Migrator</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Sign in to continue</p>
        </div>
        <div className="bg-[var(--panel-bg)] rounded-xl border border-[var(--panel-border)] shadow-sm p-6">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-muted)]">Username</label>
              <input className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                     value={username} onChange={e=>setUsername(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-muted)]">Password</label>
              <input type="password"
                     className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                     value={password} onChange={e=>setPassword(e.target.value)} />
            </div>
            <button className="w-full inline-flex justify-center rounded-lg bg-[var(--accent)] px-4 py-2 text-white font-medium hover:bg-[var(--accent-hover)] focus:ring-4 focus:ring-orange-200">
              Sign in
            </button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </div>
        <p className="text-center text-xs text-[var(--text-muted)] mt-4">default: admin / admin</p>
      </div>
    </div>
  )
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('token'))
  const navigate = useNavigate()
  const logout = () => { localStorage.removeItem('token'); setAuthed(false) }

  if (!authed) return <Login onLogin={()=>{ setAuthed(true); navigate('/') }} />

  return (
    <div className="min-h-screen bg-[var(--body-bg)] text-[var(--text-primary)] flex flex-col">
      <header className="bg-[var(--header-bg)] border-b border-[var(--header-border)] text-white">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl font-semibold tracking-tight">VM</span>
            <span className="text-xl font-light text-[var(--accent)]">Migrator</span>
          </div>
          <button
            onClick={logout}
            className="rounded bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"
          >
            Logout
          </button>
        </div>
        <nav className="px-4 pb-3 flex gap-2 lg:hidden">
          <NavLink
            to="/"
            end
            className={({isActive}) => `flex-1 rounded-md px-3 py-2 text-center text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'bg-[#2c2f34] text-gray-300'}`}
          >VMs</NavLink>
          <NavLink
            to="/providers"
            className={({isActive}) => `flex-1 rounded-md px-3 py-2 text-center text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'bg-[#2c2f34] text-gray-300'}`}
          >Providers</NavLink>
          <NavLink
            to="/jobs"
            className={({isActive}) => `flex-1 rounded-md px-3 py-2 text-center text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'bg-[#2c2f34] text-gray-300'}`}
          >Jobs</NavLink>
          <NavLink
            to="/logs"
            className={({isActive}) => `flex-1 rounded-md px-3 py-2 text-center text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'bg-[#2c2f34] text-gray-300'}`}
          >Logs</NavLink>
        </nav>
        <div className="h-1 bg-[var(--accent)]" />
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden lg:flex lg:w-64 bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] text-gray-200 flex-col">
          <div className="px-4 py-3 text-xs uppercase tracking-wide text-gray-400">Navigation</div>
          <nav className="flex-1 px-2 space-y-1">
            <NavLink
              to="/"
              end
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'text-gray-300 hover:bg-[#32363c] hover:text-white'}`}
            >VMs</NavLink>
            <NavLink
              to="/providers"
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'text-gray-300 hover:bg-[#32363c] hover:text-white'}`}
            >Providers</NavLink>
            <NavLink
              to="/jobs"
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'text-gray-300 hover:bg-[#32363c] hover:text-white'}`}
            >Jobs</NavLink>
            <NavLink
              to="/logs"
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm transition-colors ${isActive ? 'bg-[var(--accent)] text-white' : 'text-gray-300 hover:bg-[#32363c] hover:text-white'}`}
            >Logs</NavLink>
          </nav>
        </aside>

        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
