import React, { useEffect, useState } from 'react'
import { API, http, authHeaders } from './api'
type Provider = { id:number; name:string; type:'proxmox'|'vcenter' }
type VMRow = { name: string; selected: boolean }

export default function VMsPage(){
  const [providers,setProviders]=useState<Provider[]>([])
  const [providerId,setProviderId]=useState<number|undefined>(undefined)
  const [vms,setVMs]=useState<VMRow[]>([])
  const [busy,setBusy]=useState(false)

  const loadProviders = async()=> {
    const res = await http.get(`${API}/api/providers`, { headers: authHeaders() })
    setProviders(res.data)
    if(res.data.length && providerId==null) setProviderId(res.data[0].id)
  }
  const loadVMs = async(pid?:number)=> {
    const res = await http.get(`${API}/api/vms`, { params: pid? { provider_id: pid } : {}, headers: authHeaders() })
    setVMs(res.data.map((n:string)=>({name:n, selected:false})))
  }
  useEffect(()=>{ loadProviders() },[])
  useEffect(()=>{ if(providerId!=null) loadVMs(providerId) },[providerId])

  const toggle=(i:number)=> setVMs(v=> v.map((r,idx)=> idx===i? {...r, selected:!r.selected}: r))
  const selectAll=()=> setVMs(v=> v.map(r=> ({...r, selected:true})))
  const clearAll=()=> setVMs(v=> v.map(r=> ({...r, selected:false})))

  const createBatch = async()=> {
    const names = vms.filter(v=>v.selected).map(v=>v.name)
    if(!names.length || providerId==null) return
    setBusy(true)
    try{
      await http.post(`${API}/api/jobs/batch`, { provider_id: providerId, vm_names: names }, { headers: authHeaders() })
      alert(`Created ${names.length} jobs`)
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Discover VMs</h2>
            <p className="text-sm text-gray-500">Select a provider, refresh, and queue batch migrations.</p>
          </div>
          <div className="flex gap-2">
            <button className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50" onClick={selectAll}>Select all</button>
            <button className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50" onClick={clearAll}>Clear</button>
            <button className="rounded-lg bg-indigo-600 px-3 py-2 text-white hover:bg-indigo-700 disabled:opacity-60"
                    disabled={busy} onClick={createBatch}>Create Batch Jobs</button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-sm text-gray-600">Provider</label>
            <select className="mt-1 rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500"
                    value={providerId??''} onChange={e=>setProviderId(Number(e.target.value))}>
              {providers.map(p=> <option key={p.id} value={p.id}>{p.name} ({p.type})</option>)}
            </select>
          </div>
          <button className="rounded-lg border border-gray-300 px-3 py-2 hover:bg-gray-50"
                  onClick={()=> providerId!=null && loadVMs(providerId)}>
            Refresh
          </button>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2"></th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">VM Name</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {vms.map((v,idx)=>(
                <tr key={v.name}>
                  <td className="px-3 py-2"><input type="checkbox" className="accent-indigo-600" checked={v.selected} onChange={()=>toggle(idx)}/></td>
                  <td className="px-3 py-2">{v.name}</td>
                </tr>
              ))}
              {!vms.length && <tr><td className="px-3 py-6 text-gray-500" colSpan={2}>No VMs found.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
