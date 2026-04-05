import { useState, useEffect, useCallback } from 'react'
import { ScanLine, RefreshCw, AlertCircle, Clock } from 'lucide-react'
import { api, type DreameMapResponse } from '../lib/api'

export default function MapPage() {
  const [mapData, setMapData] = useState<DreameMapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isTimeout, setIsTimeout] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const fetchMap = useCallback(async () => {
    setLoading(true)
    setError(null)
    setIsTimeout(false)
    try {
      const data = await api.getMap()
      if (data.timeout) {
        // Backend returned a timeout response (not an HTTP error)
        setError(data.error as string || 'Map request timed out')
        setIsTimeout(true)
        setMapData(null)
      } else {
        setMapData(data)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to load map'
      setError(msg)
      setIsTimeout(msg.toLowerCase().includes('timed out'))
      setMapData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMap()
  }, [fetchMap])

  const imageUrl = mapData?.image_url && typeof mapData.image_url === 'string' ? mapData.image_url : null
  const imageBase64 =
    mapData?.image && typeof mapData.image === 'string'
      ? mapData.image.startsWith('data:')
        ? mapData.image
        : `data:image/png;base64,${mapData.image}`
      : null

  return (
    <div className="flex flex-col py-4 px-4 sm:px-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <ScanLine className="text-amber-400 w-8 h-8" />
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">LIDAR Map</h1>
            <p className="text-slate-400 text-sm">Dreame D20 Pro floor map and obstacle data</p>
          </div>
        </div>
        <button
          type="button"
          onClick={fetchMap}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 hover:bg-white/10 text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-24 text-slate-500">
          <RefreshCw className="w-8 h-8 animate-spin mr-2" />
          Loading map…
        </div>
      )}

      {error && (
        <div className={`flex items-start gap-3 p-4 rounded-2xl border ${
          isTimeout
            ? 'border-blue-500/20 bg-blue-500/10 text-blue-200'
            : 'border-amber-500/20 bg-amber-500/10 text-amber-200'
        }`}>
          {isTimeout ? (
            <Clock className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <div>
            <p className="font-medium">{isTimeout ? 'Map request timed out' : 'Map unavailable'}</p>
            <p className="text-sm opacity-80 mt-1">{error}</p>
            {isTimeout && (
              <p className="text-xs text-slate-400 mt-2">
                The DreameHome cloud may be slow or unreachable. Try again in a moment.
              </p>
            )}
            {!isTimeout && (
              <p className="text-xs text-slate-400 mt-2">
                Ensure the backend is running, or set <span className="text-slate-300">VITE_DREAME_MAP_URL</span> to an alternate map endpoint. Default: GET /api/v1/map
              </p>
            )}
          </div>
        </div>
      )}

      {!loading && !error && mapData && (
        <div className="flex flex-col gap-6">
          {(imageUrl || imageBase64) ? (
            <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 overflow-hidden">
              <img
                src={imageUrl || imageBase64 || ''}
                alt="Dreame map"
                className="w-full h-auto max-h-[70vh] object-contain bg-black/40"
              />
              <p className="p-2 text-xs text-slate-500 border-t border-white/5">Source: Dreame D20 Pro</p>
            </div>
          ) : (
            <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4">
              <p className="text-slate-400 text-sm mb-2">Map endpoint returned JSON (no image). Keys: {Object.keys(mapData).join(', ')}</p>
            </div>
          )}
          <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowRaw((v) => !v)}
              className="w-full px-4 py-3 flex items-center justify-between text-left text-sm font-medium text-slate-300 hover:bg-white/5"
            >
              <span>Raw response</span>
              <span className="text-slate-500">{showRaw ? 'Hide' : 'Show'}</span>
            </button>
            {showRaw && (
              <pre className="p-4 pt-0 text-xs text-slate-400 overflow-auto max-h-64 border-t border-white/5 font-mono whitespace-pre-wrap break-all">
                {JSON.stringify(mapData, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}

      {!loading && !error && !mapData && <p className="text-slate-500 text-sm">No map data returned.</p>}
    </div>
  )
}
