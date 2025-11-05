import React, { useEffect, useRef, useState } from 'react'
import { API } from './api'

type Props = {
  jobId: number | null
  onClose: () => void
}

export default function JobDrawer({ jobId, onClose }: Props){
  const [logs, setLogs] = useState<string[]>([])
  const [progress, setProgress] = useState<number>(0)
  const [status, setStatus] = useState<string>('running')
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(()=> {
    if (jobId == null) return
    let es: EventSource | null = null
    let closed = false

    const token = localStorage.getItem('token') || ''
    const start = async () => {
      // initial logs
      const res = await fetch(`${API}/api/jobs/${jobId}/logs`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const data = await res.json()
      setLogs(data.map((r:any)=> r.message))
      // stream
      es = new EventSource(`${API}/api/jobs/${jobId}/stream?token=${encodeURIComponent(token)}`)
      es.onmessage = (ev) => setLogs(prev => [...prev, ev.data])
      es.addEventListener('progress', (ev:any) => {
        const v = Number((ev as MessageEvent).data)
        if (!Number.isNaN(v)) setProgress(v)
      })
      es.addEventListener('done', (ev:any) => {
        const s = String((ev as MessageEvent).data || 'completed')
        setStatus(s); setProgress(100)
        es?.close(); es = null
      })
      es.onerror = () => { /* network flap; browser will reconnect automatically */ }
    }
    start()

    return () => { closed = true; es?.close() }
  }, [jobId])

  useEffect(()=> {
    // autoscroll logs
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [logs])

  const open = jobId != null

  return (
    <div className={`fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`}>
      {/* backdrop */}
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/40 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}
      />
      {/* panel */}
      <div className={`absolute right-0 top-0 h-full w-full max-w-md bg-[var(--panel-bg)] shadow-xl border-l border-[var(--panel-border)]
                       transition-transform ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="p-4 border-b border-[var(--panel-border)] flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Job #{jobId} – <span className="text-[var(--text-muted)]">{status}</span></h3>
          <button className="rounded-md border border-[var(--panel-border)] px-2 py-1 text-sm hover:bg-gray-100" onClick={onClose}>Close</button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-[var(--accent)] transition-all" style={{ width: `${progress}%` }} />
            </div>
            <div className="text-xs text-[var(--text-muted)] mt-1">{progress}%</div>
          </div>

          <div>
            <div className="text-sm font-medium text-[var(--text-primary)] mb-2">Live Logs</div>
            <div ref={logRef} className="h-[50vh] overflow-auto rounded-lg border border-[var(--panel-border)] bg-gray-100 p-3 text-sm leading-6">
              {logs.map((line, idx)=> (
                <div key={idx} className="font-mono text-gray-700">{line}</div>
              ))}
              {!logs.length && <div className="text-gray-400">No logs yet…</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
