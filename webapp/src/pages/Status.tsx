import {
  Activity,
  AlertCircle,
  Battery,
  RefreshCw,
  Server,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type DreameStatus, type Health } from "../lib/api";

function errMessage(e: unknown): string {
  if (e instanceof Error) {
    return e.message;
  }
  return String(e);
}

export default function Status() {
  const [health, setHealth] = useState<Health | null>(null);
  const [status, setStatus] = useState<DreameStatus | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = useCallback(() => {
    setLoading(true);
    setErr(null);
    setHealthErr(null);
    void Promise.allSettled([api.getHealth(), api.getStatus()]).then(
      (results) => {
        const [h, s] = results;
        if (h.status === "fulfilled") {
          setHealth(h.value);
          setHealthErr(null);
        } else {
          setHealth(null);
          setHealthErr(errMessage(h.reason));
        }
        if (s.status === "fulfilled") {
          setStatus(s.value);
          setErr(null);
        } else {
          setStatus(null);
          setErr(errMessage(s.reason));
        }
        setLoading(false);
      },
    );
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 10000);
    return () => clearInterval(t);
  }, [fetchAll]);

  if (loading && !status && !health) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="w-8 h-8 animate-spin text-amber-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 py-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Activity className="text-amber-400 w-8 h-8" />
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Status
            </h1>
            <p className="text-slate-400 text-sm">
              Health API plus battery and robot state
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={fetchAll}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {healthErr && (
        <div className="flex items-center gap-3 p-4 rounded-2xl border border-rose-500/20 bg-rose-500/10 text-rose-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">
            <span className="font-semibold text-rose-100">Health API: </span>
            {healthErr}
          </p>
        </div>
      )}

      {health && (
        <div className="rounded-2xl border border-indigo-500/20 bg-indigo-950/40 p-5">
          <div className="flex items-center gap-3 mb-4">
            <Server className="w-5 h-5 text-indigo-300" />
            <h2 className="text-sm font-bold text-slate-200">
              Backend (GET /api/v1/health)
            </h2>
          </div>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-slate-500">status</dt>
              <dd className="font-mono text-slate-200">{health.status}</dd>
            </div>
            <div>
              <dt className="text-slate-500">service</dt>
              <dd className="font-mono text-slate-200">
                {health.service ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">mode</dt>
              <dd className="font-mono text-slate-200">{health.mode ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">connected</dt>
              <dd
                className={
                  health.connected ? "text-emerald-400" : "text-rose-300"
                }
              >
                {health.connected ? "true" : "false"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">local_miot</dt>
              <dd
                className={
                  health.local_miot === true
                    ? "text-emerald-400"
                    : health.local_miot === false
                      ? "text-amber-300"
                      : "text-slate-400"
                }
              >
                {health.local_miot === undefined
                  ? "—"
                  : String(health.local_miot)}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">did</dt>
              <dd className="font-mono text-slate-200 break-all">
                {health.did ?? "—"}
              </dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-slate-500">timestamp</dt>
              <dd className="font-mono text-slate-300 text-xs">
                {health.timestamp ?? "—"}
              </dd>
            </div>
          </dl>
        </div>
      )}

      {err && (
        <div className="flex items-center gap-3 p-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">
            <span className="font-semibold text-amber-100">
              Robot status API:{" "}
            </span>
            {err}
          </p>
        </div>
      )}

      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
            <div className="flex items-center gap-3 mb-2">
              <Battery className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-bold text-slate-200">Battery</h2>
            </div>
            <p className="text-3xl font-bold text-white">
              {status.battery ?? "—"}%
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-amber-400" />
              <h2 className="text-sm font-bold text-slate-200">State</h2>
            </div>
            <p className="text-xl font-bold text-white capitalize">
              {status.state ?? "—"}
            </p>
          </div>
          {status.message && (
            <p className="text-sm text-slate-500 col-span-2">
              {status.message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
