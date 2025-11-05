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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-semibold tracking-tight">VM Migrator</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to continue</p>
        </div>
        <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Username</label>
              <input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                     value={username} onChange={e=>setUsername(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input type="password"
                     className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                     value={password} onChange={e=>setPassword(e.target.value)} />
            </div>
            <button className="w-full inline-flex justify-center rounded-lg bg-indigo-600 px-4 py-2 text-white font-medium hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-200">
              Sign in
            </button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </div>
        <p className="text-center text-xs text-gray-400 mt-4">default: admin / admin</p>
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-[var(--bg)] to-[var(--bg2)] text-white">
        <div className="mx-auto max-w-7xl px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">VM Migrator</h1>
          <button
            onClick={logout}
            className="rounded-lg bg-white/10 hover:bg-white/20 px-3 py-1.5 text-sm"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="mx-auto max-w-7xl px-4 py-6 grid grid-cols-12 gap-6">
        <aside className="col-span-12 lg:col-span-3">
          <nav className="bg-white rounded-xl shadow border border-gray-200 p-3 space-y-1">
            <NavLink
              to="/"
              end
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm ${isActive ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'}`}
            >VMs</NavLink>
            <NavLink
              to="/providers"
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm ${isActive ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'}`}
            >Providers</NavLink>
            <NavLink
              to="/jobs"
              className={({isActive}) => `block rounded-md px-3 py-2 text-sm ${isActive ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'}`}
            >Jobs</NavLink>
          </nav>
        </aside>

        <main className="col-span-12 lg:col-span-9">
          <Outlet/>
        </main>
      </div>
    </div>
  )
}
