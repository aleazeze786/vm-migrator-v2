import React, { useEffect, useState } from 'react'
import { API, http, authHeaders, extractErrorMessage } from './api'

type SystemLog = {
  id: number
  level: string
  component: string
  message: string
  created_at: string
}

const levelClass = (level: string) => {
  switch (level.toUpperCase()) {
    case 'ERROR':
      return 'bg-red-50 text-red-700 ring-1 ring-red-200'
    case 'WARNING':
      return 'bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200'
    default:
      return 'bg-green-50 text-green-700 ring-1 ring-green-200'
  }
}

export default function LogsPage() {
  const [logs, setLogs] = useState<SystemLog[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await http.get(`${API}/api/logs/system`, { headers: authHeaders(), params: { limit: 100 } })
      setLogs(res.data)
      setError(null)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const id = setInterval(fetchLogs, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">System Activity</h2>
          <p className="text-sm text-[var(--text-muted)]">High-level events from provider and job operations.</p>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="rounded border border-[var(--panel-border)] px-3 py-2 text-sm hover:bg-gray-100 disabled:opacity-60"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-[var(--panel-bg)] rounded-xl border border-[var(--panel-border)] shadow-sm overflow-hidden">
        <table className="min-w-full divide-y divide-[var(--panel-border)] text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">Timestamp</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">Level</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">Component</th>
              <th className="px-3 py-2 text-left font-semibold text-gray-700">Message</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {logs.map(log => (
              <tr key={log.id}>
                <td className="px-3 py-2 text-gray-600">{new Date(log.created_at).toLocaleString()}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${levelClass(log.level)}`}>
                    {log.level}
                  </span>
                </td>
                <td className="px-3 py-2 text-gray-600 uppercase tracking-wide text-xs">{log.component}</td>
                <td className="px-3 py-2 text-gray-700">{log.message}</td>
              </tr>
            ))}
            {!logs.length && (
              <tr>
                <td className="px-3 py-6 text-center text-gray-500" colSpan={4}>
                  No events recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
