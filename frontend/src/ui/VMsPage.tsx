import React, { useEffect, useMemo, useState } from 'react'
import { API, http, authHeaders, extractErrorMessage } from './api'

type Provider = {
  id: number
  name: string
  type: 'proxmox' | 'vcenter'
}

type VM = {
  id: number
  name: string
  power_state?: string
  cpu_count?: number
  memory_bytes?: number
  selected: boolean
}

type ProxmoxNode = {
  id: number
  name: string
}

const fmtGiB = (bytes?: number) => {
  if (!bytes) return '—'
  return `${(bytes / (1024 ** 3)).toFixed(1)} GiB`
}

export default function VMsPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [sourceProviderId, setSourceProviderId] = useState<number | null>(null)
  const [destProviderId, setDestProviderId] = useState<number | null>(null)
  const [targetNodes, setTargetNodes] = useState<ProxmoxNode[]>([])
  const [targetNode, setTargetNode] = useState<string>('')
  const [vms, setVMs] = useState<VM[]>([])
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<{ type:'success'|'error'; message:string }|null>(null)
  const headers = useMemo(() => ({ headers: authHeaders() }), [])

  const loadProviders = async () => {
    const res = await http.get(`${API}/api/providers`, headers)
    const src = res.data.filter((p: Provider) => p.type === 'vcenter')
    const dst = res.data.filter((p: Provider) => p.type === 'proxmox')
    setProviders(res.data)
    if (sourceProviderId == null && src.length) setSourceProviderId(src[0].id)
    if (destProviderId == null && dst.length) setDestProviderId(dst[0].id)
  }

  const loadVMs = async (pid: number) => {
    const res = await http.get(`${API}/api/vms`, { ...headers, params: { provider_id: pid } })
    setVMs(
      res.data.map((vm: any) => ({
        id: vm.id,
        name: vm.name,
        power_state: vm.power_state,
        cpu_count: vm.cpu_count,
        memory_bytes: vm.memory_bytes,
        selected: false,
      }))
    )
  }

  const loadNodes = async (pid: number) => {
    const res = await http.get(`${API}/api/providers/${pid}/nodes`, headers)
    setTargetNodes(res.data)
    if (res.data.length) setTargetNode(res.data[0].name)
    else setTargetNode('')
  }

  const syncProvider = async (pid: number | null) => {
    if (pid == null) return
    setBusy(true)
    try {
      await http.post(`${API}/api/providers/${pid}/sync`, {}, headers)
      const provider = providers.find((p) => p.id === pid)
      if (provider?.type === 'vcenter') {
        await loadVMs(pid)
        setStatus({ type:'success', message:`Synced vCenter provider '${provider.name}'.` })
      }
      if (provider?.type === 'proxmox') {
        await loadNodes(pid)
        setStatus({ type:'success', message:`Synced Proxmox provider '${provider.name}'.` })
      }
    } catch (err) {
      setStatus({ type:'error', message: extractErrorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    loadProviders()
  }, [])

  useEffect(() => {
    if (sourceProviderId != null) loadVMs(sourceProviderId)
  }, [sourceProviderId])

  useEffect(() => {
    if (destProviderId != null) loadNodes(destProviderId)
  }, [destProviderId])

  const toggle = (idx: number) =>
    setVMs((rows) =>
      rows.map((row, i) => (i === idx ? { ...row, selected: !row.selected } : row))
    )

  const selectAll = () => setVMs((rows) => rows.map((row) => ({ ...row, selected: true })))
  const clearAll = () => setVMs((rows) => rows.map((row) => ({ ...row, selected: false })))

  const createBatch = async () => {
    if (busy) return
    if (sourceProviderId == null || destProviderId == null) {
      setStatus({ type:'error', message:'Select both source (vCenter) and destination (Proxmox) providers.' })
      return
    }
    const selectedIds = vms.filter((v) => v.selected).map((v) => v.id)
    if (!selectedIds.length) {
      setStatus({ type:'error', message:'Select at least one VM to migrate.' })
      return
    }
    setBusy(true)
    try {
      await http.post(
        `${API}/api/jobs/batch`,
        {
          source_provider_id: sourceProviderId,
          destination_provider_id: destProviderId,
          source_vm_ids: selectedIds,
          target_node: targetNode || undefined,
        },
        headers
      )
      setStatus({ type:'success', message:`Queued ${selectedIds.length} migration job(s).` })
      clearAll()
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Plan VMware → Proxmox migrations</h2>
            <p className="text-sm text-[var(--text-muted)]">
              Sync a vCenter provider to discover VMs, pick a Proxmox cluster as the destination,
              then queue migration jobs.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="rounded border border-[var(--panel-border)] px-3 py-2 text-sm hover:bg-gray-100"
              onClick={selectAll}
            >
              Select all
            </button>
            <button
              className="rounded border border-[var(--panel-border)] px-3 py-2 text-sm hover:bg-gray-100"
              onClick={clearAll}
            >
              Clear
            </button>
            <button
              className="rounded bg-[var(--accent)] px-3 py-2 text-white text-sm hover:bg-[var(--accent-hover)] disabled:opacity-60"
              disabled={busy}
              onClick={createBatch}
            >
              Queue batch jobs
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-[var(--panel-border)] bg-white/60 p-4 space-y-3">
            <div>
              <label className="block text-sm text-[var(--text-muted)]">Source vCenter</label>
              <select
                className="mt-1 w-full rounded-lg border border-[var(--panel-border)] bg-white px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                value={sourceProviderId ?? ''}
                onChange={(e) => setSourceProviderId(Number(e.target.value) || null)}
              >
                <option value="" disabled>
                  Select provider
                </option>
                {providers
                  .filter((p) => p.type === 'vcenter')
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
            <button
              className="rounded border border-[var(--accent)] px-3 py-2 text-sm text-[var(--accent)] hover:bg-[var(--accent)]/10 disabled:opacity-50"
              disabled={busy || sourceProviderId == null}
              onClick={() => syncProvider(sourceProviderId)}
            >
              Sync vCenter inventory
            </button>
          </div>

          <div className="rounded-lg border border-[var(--panel-border)] bg-white/60 p-4 space-y-3">
            <div>
              <label className="block text-sm text-[var(--text-muted)]">Destination Proxmox</label>
              <select
                className="mt-1 w-full rounded-lg border border-[var(--panel-border)] bg-white px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                value={destProviderId ?? ''}
                onChange={(e) => setDestProviderId(Number(e.target.value) || null)}
              >
                <option value="" disabled>
                  Select provider
                </option>
                {providers
                  .filter((p) => p.type === 'proxmox')
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--text-muted)]">Target node</label>
              <select
                className="mt-1 w-full rounded-lg border border-[var(--panel-border)] bg-white px-3 py-2 focus:ring-2 focus:ring-[var(--accent)]"
                value={targetNode}
                onChange={(e) => setTargetNode(e.target.value)}
              >
                {targetNodes.map((node) => (
                  <option key={node.id} value={node.name}>
                    {node.name}
                  </option>
                ))}
                {!targetNodes.length && <option value="">No nodes discovered</option>}
              </select>
            </div>
            <button
              className="rounded border border-[var(--accent)] px-3 py-2 text-sm text-[var(--accent)] hover:bg-[var(--accent)]/10 disabled:opacity-50"
              disabled={busy || destProviderId == null}
              onClick={() => syncProvider(destProviderId)}
            >
              Sync Proxmox nodes
            </button>
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full divide-y divide-[var(--panel-border)] text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-3 py-2"></th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Name</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Power</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">vCPU</th>
                <th className="px-3 py-2 text-left font-semibold text-gray-700">Memory</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {vms.map((vm, idx) => (
                <tr key={vm.id}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      className="accent-indigo-600"
                      checked={vm.selected}
                      onChange={() => toggle(idx)}
                    />
                  </td>
                  <td className="px-3 py-2">{vm.name}</td>
                  <td className="px-3 py-2 text-gray-600">{vm.power_state ?? 'unknown'}</td>
                  <td className="px-3 py-2">{vm.cpu_count ?? '—'}</td>
                  <td className="px-3 py-2 text-gray-600">{fmtGiB(vm.memory_bytes)}</td>
                </tr>
              ))}
              {!vms.length && (
                <tr>
                  <td className="px-3 py-6 text-gray-500" colSpan={5}>
                    No VMs discovered. Sync your vCenter provider first.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
