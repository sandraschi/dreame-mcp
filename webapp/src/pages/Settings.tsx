import { Bot, Plug, RefreshCw, Settings as SettingsIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type ConnectionInfo } from "../lib/api";
import { useLlmStore } from "../store/llm";

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export default function Settings() {
  const { providerOk, models, selectedModel, discover, setModel } =
    useLlmStore();

  const [conn, setConn] = useState<ConnectionInfo | null>(null);
  const [connErr, setConnErr] = useState<string | null>(null);
  const [connLoading, setConnLoading] = useState(true);
  const [ip, setIp] = useState("");
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [country, setCountry] = useState("eu");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [testErr, setTestErr] = useState<string | null>(null);

  const fetchConn = useCallback(() => {
    setConnLoading(true);
    setConnErr(null);
    api
      .getConnection()
      .then((c) => {
        setConn(c);
        setIp(c.ip ?? "");
        if (c.user) setUser(c.user);
        setCountry(c.country ?? "eu");
      })
      .catch((e: unknown) => setConnErr(errText(e)))
      .finally(() => setConnLoading(false));
  }, []);

  useEffect(() => {
    discover();
    fetchConn();
  }, [discover, fetchConn]);

  const testConn = () => {
    setTesting(true);
    setTestMsg(null);
    setTestErr(null);
    api
      .testConnection({ ip, user, password, country })
      .then((r) => {
        if (r.success) {
          setTestMsg(
            `Test OK — these settings connect (${r.mode ?? "live"}). Safe to save.`,
          );
        } else {
          setTestErr(
            `Test failed — nothing saved: ${r.error ?? "unknown error"}`,
          );
        }
      })
      .catch((e: unknown) => setTestErr(`Test failed: ${errText(e)}`))
      .finally(() => setTesting(false));
  };

  const saveConn = () => {
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    api
      .updateConnection({ ip, user, password, country })
      .then((r) => {
        setConn(r.connection);
        setPassword("");
        const mode = r.connection.mode;
        setSaveMsg(
          `Saved (${r.updated.join(", ") || "nothing changed"}) — backend is now: ${mode}.`,
        );
      })
      .catch((e: unknown) => setSaveErr(errText(e)))
      .finally(() => setSaving(false));
  };

  return (
    <div className="space-y-6 py-4 max-w-4xl">
      <div className="flex items-center gap-4">
        <SettingsIcon className="text-amber-400 w-8 h-8" />
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Settings
          </h1>
          <p className="text-slate-400 text-sm">
            Robot connection and backend configuration
          </p>
        </div>
      </div>

      <div
        className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5"
        data-testid="settings-connection-section"
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Plug className="w-4 h-4 text-amber-400" />
            Robot connection
          </h2>
          <button
            type="button"
            onClick={fetchConn}
            disabled={connLoading}
            data-testid="settings-connection-refresh"
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 text-xs disabled:opacity-50"
          >
            <RefreshCw
              size={12}
              className={connLoading ? "animate-spin" : ""}
            />
            Refresh
          </button>
        </div>

        {connErr && (
          <p
            className="text-sm text-rose-300 mb-3"
            data-testid="settings-connection-error"
          >
            Connection API: {connErr}
          </p>
        )}

        {conn && (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-4">
            <div>
              <dt className="text-slate-500">mode</dt>
              <dd
                className="font-mono text-slate-200"
                data-testid="settings-connection-status"
              >
                {conn.mode}
                {conn.connected ? " (connected)" : ""}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">robot IP</dt>
              <dd className="font-mono text-slate-200">{conn.ip ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">device ID</dt>
              <dd className="font-mono text-slate-200 break-all">
                {conn.did ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">DreameHome account</dt>
              <dd className="font-mono text-slate-200">
                {conn.user ?? (conn.user_set ? "(set, hidden)" : "—")}
                {conn.password_set ? "" : " (no password stored)"}
              </dd>
            </div>
            {(conn.startup_error ?? conn.cloud_error) && (
              <div className="sm:col-span-2">
                <dt className="text-slate-500">last error</dt>
                <dd className="text-amber-300/90 text-xs leading-relaxed">
                  {conn.startup_error ?? conn.cloud_error}
                </dd>
              </div>
            )}
          </dl>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm border-t border-white/5 pt-4">
          <label className="flex flex-col gap-1">
            <span className="text-slate-400 text-xs">Robot IP (DREAME_IP)</span>
            <input
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              placeholder="192.168.0.x — empty for cloud only"
              data-testid="settings-connection-ip"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-sm font-mono"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400 text-xs">
              DreameHome account (DREAME_USER)
            </span>
            <input
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="email or phone"
              data-testid="settings-connection-user"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400 text-xs">
              DreameHome password (DREAME_PASSWORD)
            </span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="blank = keep stored password"
              data-testid="settings-connection-password"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400 text-xs">
              Cloud region (DREAME_COUNTRY)
            </span>
            <input
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="eu"
              data-testid="settings-connection-country"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-sm font-mono"
            />
          </label>
        </div>

        <div className="flex items-center gap-3 mt-4 flex-wrap">
          <button
            type="button"
            onClick={testConn}
            disabled={testing || saving}
            data-testid="settings-connection-test"
            className="px-4 py-2 rounded-xl border border-amber-600/60 text-amber-300 text-sm font-bold hover:bg-amber-600/10 disabled:opacity-50"
          >
            {testing ? "Testing…" : "Test connection"}
          </button>
          <button
            type="button"
            onClick={saveConn}
            disabled={saving || testing}
            data-testid="settings-connection-save"
            className="px-4 py-2 rounded-xl bg-amber-600 text-white text-sm font-bold hover:bg-amber-500 disabled:opacity-50"
          >
            {saving ? "Saving + reconnecting…" : "Save + reconnect"}
          </button>
          {testMsg && (
            <p
              className="text-sm text-emerald-300"
              data-testid="settings-connection-test-ok"
            >
              {testMsg}
            </p>
          )}
          {testErr && (
            <p
              className="text-sm text-rose-300"
              data-testid="settings-connection-test-error"
            >
              {testErr}
            </p>
          )}
          {saveMsg && (
            <p
              className="text-sm text-emerald-300"
              data-testid="settings-connection-saved"
            >
              {saveMsg}
            </p>
          )}
          {saveErr && (
            <p
              className="text-sm text-rose-300"
              data-testid="settings-connection-save-error"
            >
              {saveErr}
            </p>
          )}
        </div>
        <p className="text-slate-600 text-xs mt-3 leading-relaxed">
          <strong className="text-slate-400">Test connection</strong> tries the
          form values without saving anything.{" "}
          <strong className="text-slate-400">Save + reconnect</strong> writes{" "}
          <span className="font-mono">.env</span> at the repo root and applies
          it immediately — no backend restart needed. DreameHome rate-limits
          logins (~5 attempts, and a wrong password costs one even on test):
          only test/save a password you are sure about. Test and reconnect can
          each take up to ~30s when the robot is unreachable.
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
        <h2
          className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-2"
          data-testid="settings-llm-section"
        >
          <Bot className="w-4 h-4 text-amber-400" />
          Local LLM
        </h2>
        <div className="space-y-3 text-sm">
          <div
            className="flex items-center gap-2"
            data-testid="llm-provider-select"
          >
            <span
              className={`w-2 h-2 rounded-full ${providerOk === null ? "bg-gray-500 animate-pulse" : providerOk ? "bg-green-500" : "bg-red-500"}`}
            />
            <span className="text-slate-300">
              Ollama (:11434) —{" "}
              {providerOk === null
                ? "probing..."
                : providerOk
                  ? "detected"
                  : "not found"}
            </span>
          </div>
          {providerOk === false && (
            <p className="text-sm text-amber-300/90">
              Install Ollama or LM Studio to enable AI features.
            </p>
          )}
          {models.length > 0 && (
            <div className="flex items-center gap-3">
              <label htmlFor="llm-model" className="text-slate-400 text-sm">
                Model
              </label>
              <select
                id="llm-model"
                data-testid="llm-model-select"
                value={selectedModel}
                onChange={(e) => setModel(e.target.value)}
                className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-sm"
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5 space-y-3 text-sm text-slate-400">
        <p className="text-slate-500 text-xs border-b border-white/5 pb-3">
          v0.2+ uses{" "}
          <strong className="text-slate-300">DreameHome cloud</strong> (
          <code className="text-amber-400/90">DREAME_USER</code> /{" "}
          <code className="text-amber-400/90">DREAME_PASSWORD</code>). Set those
          in the <strong className="text-slate-300">Robot connection</strong>{" "}
          card above — or directly in{" "}
          <code className="text-amber-400/90">.env</code> at the repo root
          before launch.
        </p>
        <p>
          <strong className="text-slate-300">DREAME_USER</strong> — DreameHome
          account (email or phone)
        </p>
        <p>
          <strong className="text-slate-300">DREAME_PASSWORD</strong> —
          DreameHome password
        </p>
        <p>
          <strong className="text-slate-300">DREAME_COUNTRY</strong> — Cloud
          region (default <code className="text-amber-400/90">eu</code>)
        </p>
        <p>
          <strong className="text-slate-300">DREAME_DID</strong> — Device ID
          (optional; auto-discovered if one device)
        </p>
        <p>
          <strong className="text-slate-300">DREAME_AUTH_KEY</strong> — Optional
          refresh token from a previous login
        </p>
        <p>
          <strong className="text-slate-300">DREAME_REF_PATH</strong> — Path to
          Tasshack ref clone (default{" "}
          <code className="text-amber-400/90">
            D:/Dev/repos/external/tasshack_dreame_vacuum_ref
          </code>
          )
        </p>
        <p>
          <strong className="text-slate-300">DREAME_MCP_PORT</strong> — Backend
          listen port (default <strong className="text-slate-300">10894</strong>
          )
        </p>
        <p>
          <strong className="text-slate-300">VITE_DREAME_API_BASE</strong> —
          Webapp API base URL (optional). Empty = same-origin / Vite proxy.
        </p>
        <p>
          <strong className="text-slate-300">VITE_DREAME_MAP_URL</strong> — Full
          URL for map fetch (optional). Default{" "}
          <code className="text-amber-400/90">/api/v1/map</code>. Use for
          cross-service map (e.g. robotics-mcp).
        </p>
        <p className="text-slate-500 text-xs pt-2 border-t border-white/5">
          <strong className="text-slate-300">DREAME_IP</strong> — LAN address of
          the robot for the local path (hybrid mode). After a Wi-Fi re-pair the
          robot usually gets a new IP: update it in the{" "}
          <strong className="text-slate-300">Robot connection</strong> card
          above. <strong className="text-slate-300">DREAME_TOKEN</strong> —
          legacy local miIO; see{" "}
          <code className="text-amber-400/90">
            docs/TOKEN_AND_HOME_ASSISTANT.md
          </code>{" "}
          for historical context.
        </p>
      </div>
    </div>
  );
}
