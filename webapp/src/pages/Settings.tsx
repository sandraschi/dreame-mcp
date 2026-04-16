import { Settings as SettingsIcon } from "lucide-react";

export default function Settings() {
	return (
		<div className="space-y-6 py-4 max-w-4xl">
			<div className="flex items-center gap-4">
				<SettingsIcon className="text-amber-400 w-8 h-8" />
				<div>
					<h1 className="text-2xl font-bold text-white tracking-tight">
						Settings
					</h1>
					<p className="text-slate-400 text-sm">
						Backend configuration via environment variables
					</p>
				</div>
			</div>
			<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5 space-y-3 text-sm text-slate-400">
				<p className="text-slate-500 text-xs border-b border-white/5 pb-3">
					v0.2+ uses{" "}
					<strong className="text-slate-300">DreameHome cloud</strong> (
					<code className="text-amber-400/90">DREAME_USER</code> /{" "}
					<code className="text-amber-400/90">DREAME_PASSWORD</code>). Set those
					in the environment or in{" "}
					<code className="text-amber-400/90">webapp/start.ps1</code> before
					launch.
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
						D:/Dev/repos/tasshack_dreame_vacuum_ref
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
					<strong className="text-slate-300">DREAME_IP</strong> /{" "}
					<strong className="text-slate-300">DREAME_TOKEN</strong> — Legacy
					local miIO; not used by the cloud server. See{" "}
					<code className="text-amber-400/90">
						docs/TOKEN_AND_HOME_ASSISTANT.md
					</code>{" "}
					for historical context.
				</p>
			</div>
		</div>
	);
}
