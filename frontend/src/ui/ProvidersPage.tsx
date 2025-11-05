import React, { useEffect, useState } from 'react'
import { API, http, authHeaders, extractErrorMessage } from './api'

type Provider = { id:number; name:string; type:'proxmox'|'vcenter'; api_url:string; username?:string; verify_ssl:boolean }

export default function ProvidersPage(){
  const [items,setItems] = useState<Provider[]>([])
  const [form,setForm] = useState<Partial<Provider & {secret?:string}>>({ type:'proxmox', verify_ssl:true })
  const [status,setStatus] = useState<{ type:'success'|'error'; message:string }|null>(null)
  const [busy,setBusy] = useState(false)

  const load = async()=> setItems((await http.get(`${API}/api/providers`, { headers: authHeaders() })).data)
  useEffect(()=>{ load() },[])

  const submit = async(e:React.FormEvent)=>{
    e.preventDefault()
    setBusy(true)
    try {
      await http.post(`${API}/api/providers`, form, { headers: authHeaders() })
      setForm({ type:'proxmox', verify_ssl:true })
      setStatus({ type:'success', message:'Provider added successfully.' })
      load()
    } catch (err) {
      setStatus({ type:'error', message: extractErrorMessage(err) })
    } finally {
      setBusy(false)
    }
  }
  const del = async(id:number)=>{
    try {
      await http.delete(`${API}/api/providers/${id}`, { headers: authHeaders() })
      setStatus({ type:'success', message:'Provider deleted.' })
      load()
    } catch (err) {
      setStatus({ type:'error', message: extractErrorMessage(err) })
    }
  }
  const sync = async(id:number)=>{
    setBusy(true)
    try {
      const res = await http.post(`${API}/api/providers/${id}/sync`, {}, { headers: authHeaders() })
      const detail = Object.entries(res.data)
        .filter(([key])=> key !== 'ok')
        .map(([key,val])=> `${key}: ${val}`)
        .join(', ')
      setStatus({ type:'success', message: `Sync complete${detail ? ` (${detail})` : ''}` })
      load()
    } catch (err) {
      setStatus({ type:'error', message: extractErrorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-[var(--panel-bg)] rounded-xl border border-[var(--panel-border)] shadow-sm p-6 space-y-4">
        {status && (
          <div
            className={`rounded-lg border px-3 py-2 text-sm ${status.type === 'error' ? 'border-red-300 bg-red-50 text-red-700' : 'border-green-300 bg-green-50 text-green-700'}`}
          >
            {status.message}
          </div>
        )}
        <h2 className="text-lg font-semibold mb-4">Add Provider</h2>
        <form onSubmit={submit} className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-[var(--text-muted)]">Name</label>
            <input className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                   value={form.name||''} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-[var(--text-muted)]">Type</label>
            <select className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                    value={form.type||'proxmox'} onChange={e=>setForm(f=>({...f,type:e.target.value as any}))}>
              <option value="proxmox">Proxmox VE</option>
              <option value="vcenter">VMware vCenter / ESXi</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm text-[var(--text-muted)]">API URL</label>
            <input className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                   placeholder="https://host:port"
                   value={form.api_url||''} onChange={e=>setForm(f=>({...f,api_url:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-[var(--text-muted)]">Username</label>
            <input className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                   value={form.username||''} onChange={e=>setForm(f=>({...f,username:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-[var(--text-muted)]">Password / Token</label>
            <input type="password" className="mt-1 w-full rounded-lg border border-[var(--panel-border)] px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                   value={form.secret||''} onChange={e=>setForm(f=>({...f,secret:e.target.value}))}/>
          </div>
          <div className="sm:col-span-2">
            <label className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <input type="checkbox" className="rounded border-gray-300" checked={!!form.verify_ssl} onChange={e=>setForm(f=>({...f,verify_ssl:e.target.checked}))}/>
              Verify TLS/SSL
            </label>
          </div>
          <div className="sm:col-span-2">
            <button disabled={busy} className="inline-flex items-center rounded-lg bg-[var(--accent)] px-4 py-2 text-white font-medium hover:bg-[var(--accent-hover)] disabled:opacity-60">
              Save
            </button>
          </div>
        </form>
      </div>

      <div className="bg-[var(--panel-bg)] rounded-xl border border-[var(--panel-border)] shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Providers</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--panel-border)] text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Name</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Type</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">API URL</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {items.map(p=> (
                <tr key={p.id}>
                  <td className="px-3 py-2">{p.id}</td>
                  <td className="px-3 py-2">{p.name}</td>
                  <td className="px-3 py-2">{p.type}</td>
                  <td className="px-3 py-2">{p.api_url}</td>
                  <td className="px-3 py-2 text-right space-x-2">
                    <button className="rounded border border-[var(--accent)] px-3 py-1.5 text-sm text-[var(--accent)] hover:bg-[var(--accent)]/10 disabled:opacity-60"
                            disabled={busy}
                            onClick={()=>sync(p.id)}>
                      Sync
                    </button>
                    <button className="rounded-lg border border-red-200 px-3 py-1.5 text-red-600 hover:bg-red-50"
                            onClick={()=>del(p.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {!items.length && (
                <tr><td className="px-3 py-6 text-gray-500" colSpan={5}>No providers yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
