import { Activity, AlertCircle, Bot } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Health } from "../lib/api";

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .getHealth()
      .then(setHealth)
      .catch((e) => setErr(e.message));
    const t = setInterval(
      () =>
        api
          .getHealth()
          .then(setHealth)
          .catch(() => {}),
      5000,
    );
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-6 py-4 max-w-4xl">
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
      </div>

      {err && (
        <div className="flex items-center gap-3 p-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 text-amber-200">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">
            {err}. Run webapp\\start.ps1 to start the backend.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-200">Backend</h2>
          </div>
          <p className="text-2xl font-bold text-white">
            {health?.status === "ok" ? "OK" : "—"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Service: {health?.service ?? "—"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Bot className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-200">Robot (miio)</h2>
          </div>
          <p className="text-2xl font-bold text-white">
            {health?.connected ? "Connected" : "Not configured"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
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
