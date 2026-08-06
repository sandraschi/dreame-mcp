import { Activity, AlertCircle, Bot, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type Health } from "../lib/api";

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [restarting, setRestarting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
      setBackendOk(true);
      setErr(null);
    } catch (e) {
      setBackendOk(false);
      setErr(e instanceof Error ? e.message : "Backend unreachable");
    }
  }, []);

  useEffect(() => {
    let attempt = 0;
    let timer: number | undefined;
    const poll = async () => {
      await refresh();
      attempt = Math.min(attempt + 1, 4);
      timer = window.setTimeout(poll, 1000 * 2 ** attempt);
    };
    poll();
    return () => {
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [refresh]);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") {
            refresh();
          } else if (
            typeof event.payload === "string" &&
            event.payload.startsWith("error:")
          ) {
            setBackendOk(false);
          }
        });
      } catch {
        // Not inside Tauri — HTTP polling handles it
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, [refresh]);

  const restartBackend = useCallback(async () => {
    setRestarting(true);
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("start_backend");
    } catch {
      setRestarting(false); // not in Tauri — HTTP poll will update
    }
  }, []);

  return (
    <div className="space-y-6 py-4 max-w-4xl" data-testid="dashboard">
      <div className="flex items-center gap-4">
        <Bot className="text-amber-400 w-8 h-8" />
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Dashboard
          </h1>
          <p className="text-slate-400 text-sm">
            Dreame D20 Pro Plus: LiDAR robot vacuum-mop with auto-empty dock and
            cloud control.
          </p>
        </div>
        <div
          className="ml-auto flex items-center gap-2"
          data-testid="backend-dot"
        >
          <span
            className={`w-2 h-2 rounded-full animate-pulse ${
              backendOk === null
                ? "bg-gray-500"
                : backendOk
                  ? "bg-green-500"
                  : "bg-red-500"
            }`}
          />
          <span className="text-sm text-slate-300">
            {backendOk === null
              ? "Connecting..."
              : backendOk
                ? "Connected"
                : "Offline"}
          </span>
        </div>
      </div>

      {err && (
        <div className="flex items-center gap-3 p-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">
            {err}. Run webapp\start.ps1 to start the backend.
          </p>
          <button
            type="button"
            onClick={restartBackend}
            disabled={restarting}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-200 text-sm hover:bg-amber-500/30 disabled:opacity-50"
            data-testid="restart-backend"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${restarting ? "animate-spin" : ""}`}
            />
            {restarting ? "Restarting..." : "Restart Backend"}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div
          className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5"
          data-testid="kpi-server"
        >
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-200">Backend</h2>
          </div>
          <p className="text-2xl font-bold text-white">
            {health?.status === "ok" ? "OK" : "—"}
          </p>
          <p className="text-sm text-slate-400 mt-1">
            Service: {health?.service ?? "—"}
          </p>
        </div>
        <div
          className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5"
          data-testid="kpi-robot"
        >
          <div className="flex items-center gap-3 mb-2">
            <Bot className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-200">Robot (miio)</h2>
          </div>
          <p className="text-2xl font-bold text-white">
            {health?.connected ? "Connected" : "Not configured"}
          </p>
          <p className="text-sm text-slate-400 mt-1">
            Set DREAME_IP and DREAME_TOKEN for control
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
        <h2 className="text-sm font-bold text-slate-200 mb-3">Quick links</h2>
        <div className="flex flex-wrap gap-3">
          <a
            href="/map"
            className="px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm hover:bg-amber-500/20"
          >
            LIDAR Map
          </a>
          <a
            href="/status"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm hover:bg-white/10"
          >
            Status
          </a>
          <a
            href="/controls"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm hover:bg-white/10"
          >
            Controls
          </a>
        </div>
      </div>
    </div>
  );
}
