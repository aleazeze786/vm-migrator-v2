import React, { useEffect, useState } from 'react'
import { API, http, authHeaders } from './api'

type Provider = { id:number; name:string; type:'proxmox'|'vcenter'; api_url:string; username?:string; verify_ssl:boolean }

export default function ProvidersPage(){
  const [items,setItems] = useState<Provider[]>([])
  const [form,setForm] = useState<Partial<Provider & {secret?:string}>>({ type:'proxmox', verify_ssl:true })

  const load = async()=> setItems((await http.get(`${API}/api/providers`, { headers: authHeaders() })).data)
  useEffect(()=>{ load() },[])

  const submit = async(e:React.FormEvent)=>{ e.preventDefault(); await http.post(`${API}/api/providers`, form, { headers: authHeaders() }); setForm({ type:'proxmox', verify_ssl:true }); load() }
  const del = async(id:number)=>{ await http.delete(`${API}/api/providers/${id}`, { headers: authHeaders() }); load() }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Add Provider</h2>
        <form onSubmit={submit} className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-600">Name</label>
            <input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                   value={form.name||''} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-gray-600">Type</label>
            <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                    value={form.type||'proxmox'} onChange={e=>setForm(f=>({...f,type:e.target.value as any}))}>
              <option value="proxmox">Proxmox VE</option>
              <option value="vcenter">VMware vCenter / ESXi</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm text-gray-600">API URL</label>
            <input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                   placeholder="https://host:port"
                   value={form.api_url||''} onChange={e=>setForm(f=>({...f,api_url:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-gray-600">Username</label>
            <input className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                   value={form.username||''} onChange={e=>setForm(f=>({...f,username:e.target.value}))}/>
          </div>
          <div>
            <label className="block text-sm text-gray-600">Password / Token</label>
            <input type="password" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                   value={form.secret||''} onChange={e=>setForm(f=>({...f,secret:e.target.value}))}/>
          </div>
          <div className="sm:col-span-2">
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" className="rounded border-gray-300" checked={!!form.verify_ssl} onChange={e=>setForm(f=>({...f,verify_ssl:e.target.checked}))}/>
              Verify TLS/SSL
            </label>
          </div>
          <div className="sm:col-span-2">
            <button className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-white font-medium hover:bg-indigo-700">
              Save
            </button>
          </div>
        </form>
      </div>

      <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Providers</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Name</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Type</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">API URL</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(p=> (
                <tr key={p.id}>
                  <td className="px-3 py-2">{p.id}</td>
                  <td className="px-3 py-2">{p.name}</td>
                  <td className="px-3 py-2">{p.type}</td>
                  <td className="px-3 py-2">{p.api_url}</td>
                  <td className="px-3 py-2 text-right">
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
