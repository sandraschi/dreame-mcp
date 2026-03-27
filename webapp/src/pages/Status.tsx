import React, { useEffect, useState } from 'react'
import { Activity, Battery, RefreshCw, AlertCircle } from 'lucide-react'
import { api, type DreameStatus } from '../lib/api'

export default function Status() {
  const [status, setStatus] = useState<DreameStatus | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStatus = () => {
    setLoading(true)
    setErr(null)
    api
      .getStatus()
      .then(setStatus)
      .catch((e) => {
        setErr(e.message)
        setStatus(null)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchStatus()
    const t = setInterval(fetchStatus, 10000)
    return () => clearInterval(t)
  }, [])

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6 py-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Activity className="text-amber-400 w-8 h-8" />
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Status</h1>
            <p className="text-slate-400 text-sm">Battery and robot state</p>
          </div>
        </div>
        <button
          type="button"
          onClick={fetchStatus}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {err && (
        <div className="flex items-center gap-3 p-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">{err}</p>
        </div>
      )}

      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
            <div className="flex items-center gap-3 mb-2">
              <Battery className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-bold text-slate-200">Battery</h2>
            </div>
            <p className="text-3xl font-bold text-white">{status.battery ?? '—'}%</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-bold text-slate-200">State</h2>
            </div>
            <p className="text-xl font-bold text-white capitalize">{status.state ?? '—'}</p>
          </div>
          {status.message && (
            <p className="text-sm text-slate-500 col-span-2">{status.message}</p>
          )}
        </div>
      )}
    </div>
  )
}
