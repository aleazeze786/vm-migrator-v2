import React, { useEffect, useState } from 'react'
import { API, http, authHeaders } from './api'
import JobDrawer from './JobDrawer'

type Job = { id:number; vm_name:string; status:string; progress:number }

export default function JobsPage(){
  const [jobs,setJobs] = useState<Job[]>([])
  const [openJob, setOpenJob] = useState<number|null>(null)

  const load = async()=> setJobs((await http.get(`${API}/api/jobs`, { headers: authHeaders() })).data)
  useEffect(()=>{ load(); const id=setInterval(load, 1000); return ()=>clearInterval(id) },[])

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Jobs</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">ID</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">VM</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Status</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map(j=>(
                <tr key={j.id} className="hover:bg-gray-50 cursor-pointer" onClick={()=>setOpenJob(j.id)}>
                  <td className="px-3 py-2">{j.id}</td>
                  <td className="px-3 py-2">{j.vm_name}</td>
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
                      <div className="h-full bg-indigo-600" style={{width:`${j.progress}%`}}/>
                    </div>
                  </td>
                </tr>
              ))}
              {!jobs.length && <tr><td className="px-3 py-6 text-gray-500" colSpan={4}>No jobs yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <JobDrawer jobId={openJob} onClose={()=>setOpenJob(null)} />
    </div>
  )
}
