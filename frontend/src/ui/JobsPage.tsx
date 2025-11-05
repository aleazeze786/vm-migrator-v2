import React, { useEffect, useState } from 'react'
import { API, http, authHeaders } from './api'
import JobDrawer from './JobDrawer'

type Job = {
  id: number
  vm_name: string
  status: string
  progress: number
  source_provider_id?: number
  destination_provider_id?: number
  target_node?: string | null
}

type Provider = { id: number; name: string }

export default function JobsPage(){
  const [jobs,setJobs] = useState<Job[]>([])
  const [openJob, setOpenJob] = useState<number|null>(null)
  const [providers,setProviders] = useState<Provider[]>([])

  const loadProviders = async()=> setProviders((await http.get(`${API}/api/providers`, { headers: authHeaders() })).data)
  const load = async()=> setJobs((await http.get(`${API}/api/jobs`, { headers: authHeaders() })).data)
  useEffect(()=>{ loadProviders(); load(); const id=setInterval(load, 1000); return ()=>clearInterval(id) },[])

  const providerName = (id?: number) => providers.find(p => p.id === id)?.name ?? '—'

  return (
    <div className="space-y-6">
      <div className="bg-[var(--panel-bg)] rounded-xl border border-[var(--panel-border)] shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-4">Jobs</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--panel-border)] text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">VM</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Source</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Destination</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Status</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {jobs.map(j=>(
                <tr key={j.id} className="hover:bg-gray-50 cursor-pointer" onClick={()=>setOpenJob(j.id)}>
                  <td className="px-3 py-2">{j.id}</td>
                  <td className="px-3 py-2">{j.vm_name}</td>
                  <td className="px-3 py-2 text-gray-600">{providerName(j.source_provider_id)}</td>
                  <td className="px-3 py-2 text-gray-600">
                    {providerName(j.destination_provider_id)}
                    {j.target_node && <span className="text-gray-400"> → {j.target_node}</span>}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                      ${j.status==='completed' ? 'bg-green-50 text-green-700 ring-1 ring-green-200' :
                        j.status==='failed' ? 'bg-red-50 text-red-700 ring-1 ring-red-200' :
                        'bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200'}`}>
                      {j.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="w-56 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-[var(--accent)]" style={{width:`${j.progress}%`}}/>
                    </div>
                  </td>
                </tr>
              ))}
              {!jobs.length && <tr><td className="px-3 py-6 text-gray-500" colSpan={6}>No jobs yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <JobDrawer jobId={openJob} onClose={()=>setOpenJob(null)} />
    </div>
  )
}
