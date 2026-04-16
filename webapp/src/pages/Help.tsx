import {
	AlertTriangle,
	ExternalLink,
	FileJson,
	HelpCircle,
	Link2,
	Package,
	Play,
	Wifi,
	Wrench,
} from "lucide-react";
import { useState } from "react";

const tabs = [
	{ id: "robot", label: "The Robot", icon: Package },
	{ id: "quickstart", label: "Quick Start", icon: Play },
	{ id: "mcp", label: "MCP Server", icon: Wrench },
	{ id: "connection", label: "Connection", icon: Wifi },
	{ id: "connection-methods", label: "Connection methods", icon: Link2 },
	{ id: "map-api", label: "Map API", icon: FileJson },
	{ id: "trouble", label: "Troubleshoot", icon: AlertTriangle },
];

const Code = ({ children }: { children: string }) => (
	<code className="bg-black/40 border border-white/10 rounded px-1.5 py-0.5 text-amber-400 text-xs font-mono">
		{children}
	</code>
);

export default function Help() {
	const [tab, setTab] = useState("robot");

	return (
		<div className="space-y-6 py-4 max-w-4xl">
			<div className="flex items-center gap-4">
				<HelpCircle className="text-amber-400 w-8 h-8" />
				<div>
					<h1 className="text-2xl font-bold text-white tracking-tight">Help</h1>
					<p className="text-slate-400 text-sm">
						Dreame D20 Pro Plus MCP server — DreameHome cloud
					</p>
				</div>
			</div>

			<div className="flex flex-wrap gap-1 p-1 bg-white/5 border border-white/5 rounded-2xl w-fit">
				{tabs.map((t) => (
					<button
						type="button"
						key={t.id}
						onClick={() => setTab(t.id)}
						className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest transition-all ${
							tab === t.id
								? "bg-amber-600 text-white shadow-lg shadow-amber-600/30"
								: "text-slate-500 hover:text-slate-300"
						}`}
					>
						<t.icon size={13} />
						<span className="hidden sm:inline">{t.label}</span>
					</button>
				))}
			</div>

			<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-6 space-y-4 text-sm text-slate-400">
				{tab === "robot" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">
							Dreame D20 Pro Plus
						</h3>
						<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
							{[
								["Model", "dreame.vacuum.r2566a"],
								["Device ID", "2045852486"],
								["Navigation", "LDS LiDAR (Pathfinder)"],
								["Suction", "13,000 Pa Vormax"],
								["Brush", "HyperStream DuoBrush (anti-tangle)"],
								["Mop", "Plate mop, 350ml tank, 32 levels"],
								["Auto-empty", "5L bag, ~150 days"],
								["Side brush", "Extendable, edge sensors"],
								["Obstacle avoidance", "3D structured light"],
								["App", "DreameHome (Alibaba Cloud, EU)"],
							].map(([k, v]) => (
								<div key={k} className="flex flex-col gap-0.5">
									<span className="text-[10px] uppercase tracking-widest text-slate-600">
										{k}
									</span>
									<span className="text-slate-300">{v}</span>
								</div>
							))}
						</div>
						<p className="text-slate-500 text-xs pt-2">
							The D20 Pro Plus uses the DreameHome cloud (not Mi Home / Xiaomi).
							Local miio control is disabled by firmware — all commands go via
							the cloud API. No local token is available.
						</p>
					</>
				)}

				{tab === "quickstart" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">Quick Start</h3>
						<ol className="space-y-3 list-decimal list-inside">
							<li>
								Ensure the Tasshack ref clone exists:
								<div className="mt-1 ml-5 font-mono text-xs text-slate-400 bg-black/30 rounded px-3 py-2">
									D:\Dev\repos\tasshack_dreame_vacuum_ref\
								</div>
							</li>
							<li>
								Credentials are pre-set in <Code>webapp\start.ps1</Code>. Change
								the password after first run.
							</li>
							<li>
								Launch: <Code>mcp-central-docs\starts\dreame-start.bat</Code>
								<div className="mt-1 ml-5 text-xs text-slate-500">
									First run: installs node_modules (~60s). Subsequent runs:
									instant.
								</div>
							</li>
							<li>
								Dashboard:{" "}
								<a
									href="http://localhost:10895"
									target="_blank"
									rel="noopener noreferrer"
									className="text-amber-400 hover:underline inline-flex items-center gap-1"
								>
									http://localhost:10895 <ExternalLink size={11} />
								</a>
							</li>
							<li>
								Health check:{" "}
								<a
									href="http://localhost:10894/api/v1/health"
									target="_blank"
									rel="noopener noreferrer"
									className="text-amber-400 hover:underline inline-flex items-center gap-1"
								>
									/api/v1/health <ExternalLink size={11} />
								</a>{" "}
								— should show <Code>connected: true</Code>
							</li>
							<li>
								Use <strong className="text-slate-300">Controls</strong> page to
								start cleaning or return to dock.
							</li>
							<li>
								Use <strong className="text-slate-300">Status</strong> page to
								monitor battery and state.
							</li>
							<li>
								Use <strong className="text-slate-300">LIDAR Map</strong> page
								to fetch the floor plan.
							</li>
						</ol>
					</>
				)}

				{tab === "mcp" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">MCP Server</h3>
						<p>
							Connect your MCP client (Claude Desktop, Cursor) to the SSE
							endpoint:
						</p>
						<pre className="bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-slate-300 font-mono overflow-x-auto">{`{
  "mcpServers": {
    "dreame": {
      "url": "http://localhost:10894/sse",
      "transport": "sse"
    }
  }
}`}</pre>

						<div className="space-y-3 pt-2">
							<div>
								<p className="text-slate-300 font-semibold mb-1">
									dreame(operation)
								</p>
								<p className="text-slate-500 mb-1">
									Portmanteau tool. Operations:
								</p>
								<div className="grid grid-cols-2 gap-1 ml-2">
									{[
										["status", "Battery, state, area, time"],
										["map", "LIDAR map (PNG or raw bytes)"],
										["start_clean", "Start full clean ✅"],
										["stop", "Stop cleaning"],
										["pause", "Pause cleaning"],
										["go_home", "Return to dock ⚠️"],
										["find_robot", "Play locator sound"],
										["battery", "Battery % shortcut"],
									].map(([op, desc]) => (
										<div key={op} className="flex gap-2">
											<Code>{op}</Code>
											<span className="text-slate-500 text-xs">{desc}</span>
										</div>
									))}
								</div>
							</div>

							<div>
								<p className="text-slate-300 font-semibold mb-1">
									dreame_help(category)
								</p>
								<p className="text-slate-500">
									Categories: status, map, control, connection, agentic
								</p>
							</div>

							<div>
								<p className="text-slate-300 font-semibold mb-1">
									dreame_agentic_workflow(goal)
								</p>
								<p className="text-slate-500">
									High-level natural language goal — the LLM plans and executes
									steps using dreame() calls.
								</p>
								<p className="text-slate-600 text-xs mt-1">
									Example: "Check battery. If above 20%, start cleaning."
								</p>
							</div>
						</div>

						<div className="pt-2 flex gap-3">
							<a
								href="http://localhost:10894/docs"
								target="_blank"
								rel="noopener noreferrer"
								className="inline-flex items-center gap-1 text-amber-400 hover:underline text-xs"
							>
								Swagger UI <ExternalLink size={11} />
							</a>
							<a
								href="http://localhost:10894/api/v1/health"
								target="_blank"
								rel="noopener noreferrer"
								className="inline-flex items-center gap-1 text-amber-400 hover:underline text-xs"
							>
								Health JSON <ExternalLink size={11} />
							</a>
						</div>
					</>
				)}

				{tab === "connection" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">Connection</h3>
						<div className="space-y-3">
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
								{[
									["Backend port", "10894 (MCP SSE + REST)"],
									["Frontend port", "10895 (Vite React)"],
									["Cloud", "DreameHome EU (Alibaba Cloud)"],
									["Protocol", "HTTPS REST + MQTT push"],
									["Ref clone", "D:\\Dev\\repos\\tasshack_dreame_vacuum_ref"],
								].map(([k, v]) => (
									<div key={k} className="flex flex-col gap-0.5">
										<span className="text-[10px] uppercase tracking-widest text-slate-600">
											{k}
										</span>
										<span className="text-slate-300 text-xs font-mono">
											{v}
										</span>
									</div>
								))}
							</div>

							<div className="pt-2">
								<p className="text-slate-300 font-semibold mb-2">
									Environment variables
								</p>
								<div className="space-y-1.5">
									{[
										["DREAME_USER", "DreameHome email/phone", true],
										["DREAME_PASSWORD", "DreameHome password", true],
										["DREAME_COUNTRY", "Cloud region (default: eu)", false],
										["DREAME_DID", "Device ID (auto-discovered)", false],
										["DREAME_AUTH_KEY", "Refresh token from last login", false],
										["DREAME_REF_PATH", "Tasshack ref clone path", false],
										["DREAME_MCP_PORT", "Backend port (default: 10894)", false],
									].map(([k, v, req]) => (
										<div key={k} className="flex gap-2 items-start">
											<Code>{k as string}</Code>
											<span className="text-slate-500 text-xs">
												{v as string}
											</span>
											{req && (
												<span className="text-amber-500 text-[10px] font-bold">
													required
												</span>
											)}
										</div>
									))}
								</div>
							</div>
						</div>
					</>
				)}

				{tab === "trouble" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">
							Troubleshooting
						</h3>
						<div className="space-y-4">
							{[
								{
									problem: "Dashboard shows black screen",
									fix: "Press F12 → Console. Usually a missing lucide-react icon or React crash. Restart the bat after any code change.",
								},
								{
									problem: "Backend shows connected: false",
									fix: "DREAME_USER / DREAME_PASSWORD not set or wrong. Check webapp\\start.ps1 credentials section.",
								},
								{
									problem: "go_home (return to dock) not working",
									fix: "Known issue — action ID may be wrong for r2566a firmware. Workaround: use DreameHome app. Fix pending.",
								},
								{
									problem: 'Map shows "Map unavailable"',
									fix: "Ensure backend is connected (GET /api/v1/health shows connected: true). Map uses cloud OBJECT_NAME + file fetch; PNG render needs numpy/Pillow/py-mini-racer — raw_b64 may still work without PNG.",
								},
								{
									problem: "npm install fails on first run",
									fix: "Delete webapp\\node_modules and webapp\\package-lock.json, then re-run the bat.",
								},
								{
									problem: "uv.exe not found",
									fix: "uv must be installed. The script checks PATH then D:\\Dev\\repos\\uv-install\\uv.exe.",
								},
								{
									problem: "Port 10894 / 10895 already in use",
									fix: "The start script kills processes on those ports automatically. If it fails, run: Get-NetTCPConnection -LocalPort 10894 | Stop-Process -Id {$_.OwningProcess} -Force",
								},
							].map(({ problem, fix }) => (
								<div
									key={problem}
									className="border border-white/5 rounded-xl p-4 space-y-1.5"
								>
									<p className="text-slate-300 font-semibold">{problem}</p>
									<p className="text-slate-500 text-xs leading-relaxed">
										{fix}
									</p>
								</div>
							))}
						</div>
					</>
				)}

				{tab === "map-api" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">
							Map API (fleet consumers)
						</h3>
						<p className="text-slate-500 text-xs leading-relaxed">
							Use this contract for{" "}
							<strong className="text-slate-400">robotics-mcp</strong>,{" "}
							<strong className="text-slate-400">yahboom-mcp</strong>, or any
							HTTP client. Authoritative copy lives in the repo:{" "}
							<Code>docs/MAP_AND_ROBOTICS.md</Code> and <Code>docs/PRD.md</Code>{" "}
							§5.
						</p>
						<div className="border border-white/5 rounded-xl p-4 space-y-2 text-xs text-slate-500">
							<p>
								<span className="text-slate-300">Endpoint:</span>{" "}
								<Code>GET http://localhost:10894/api/v1/map</Code> (same JSON as
								MCP <Code>dreame(operation='map')</Code>)
							</p>
							<p>
								<span className="text-slate-300">Pattern:</span> one{" "}
								<Code>application/json</Code> body — map bytes are{" "}
								<strong className="text-slate-400">base64 inside JSON</strong>,
								not a separate binary download.
							</p>
							<ul className="list-disc list-inside space-y-1 ml-1">
								<li>
									<Code>raw_b64</Code> — raw Dreame map file (always on
									success); base64-decode for downstream decoders.
								</li>
								<li>
									<Code>image</Code> — optional base64 PNG (no{" "}
									<Code>data:</Code> prefix) when render succeeds.
								</li>
								<li>
									<Code>map_data</Code> — optional summary (rooms, positions)
									when decode succeeds.
								</li>
								<li>
									<Code>render_error</Code> — optional; <Code>raw_b64</Code>{" "}
									still present.
								</li>
							</ul>
							<p>
								<span className="text-slate-300">Errors:</span> HTTP 502 with{" "}
								<Code>
									{"{"}"detail":"…"{"}"}
								</Code>{" "}
								— check backend logs and <Code>DREAME_*</Code> env.
							</p>
							<p>
								<span className="text-slate-300">Webapp override:</span>{" "}
								<Code>VITE_DREAME_MAP_URL</Code> points the LIDAR page at
								another absolute URL if needed.
							</p>
						</div>
					</>
				)}

				{tab === "connection-methods" && (
					<>
						<h3 className="text-slate-200 font-bold text-base">
							Connection methods
						</h3>
						<div className="space-y-4">
							<div className="border border-white/5 rounded-xl p-4 space-y-2">
								<p className="text-slate-300 font-semibold">
									Method A: DreameHome cloud (used by this server)
								</p>
								<p className="text-slate-500 text-xs leading-relaxed">
									This project uses the Dreame cloud login flow with{" "}
									<Code>DREAME_USER</Code>/<Code>DREAME_PASSWORD</Code>, then
									calls Dreame cloud REST APIs and opens MQTT for push updates.
									It is the reliable path for D20 Pro Plus firmware.
								</p>
								<div className="space-y-1 text-xs text-slate-500">
									<p>
										<span className="text-slate-300">Auth:</span> Dreame account
										+ refresh token (<Code>DREAME_AUTH_KEY</Code> optional)
									</p>
									<p>
										<span className="text-slate-300">Control:</span> cloud API
										actions (start, stop, pause, locate, dock)
									</p>
									<p>
										<span className="text-slate-300">Map:</span> cloud
										object/file fetch + decode/render via Tasshack map layer
									</p>
									<p>
										<span className="text-slate-300">Pros:</span> works with
										newer Dreame-only app firmware
									</p>
									<p>
										<span className="text-slate-300">Cons:</span> depends on
										internet/cloud availability
									</p>
								</div>
							</div>

							<div className="border border-white/5 rounded-xl p-4 space-y-2">
								<p className="text-slate-300 font-semibold">
									Method B: Xiaomi / miIO local token (legacy/other models)
								</p>
								<p className="text-slate-500 text-xs leading-relaxed">
									Some Xiaomi ecosystem vacuums expose a local miIO protocol
									endpoint controlled by IP + token. On many Dreame D20 Pro Plus
									firmware builds, this local path is restricted or unavailable.
								</p>
								<div className="space-y-1 text-xs text-slate-500">
									<p>
										<span className="text-slate-300">Auth:</span> local token +
										LAN IP (<Code>DREAME_TOKEN</Code>, <Code>DREAME_IP</Code>)
									</p>
									<p>
										<span className="text-slate-300">Control:</span> direct LAN
										RPC, low latency, cloud-independent
									</p>
									<p>
										<span className="text-slate-300">Map:</span> model/firmware
										dependent; often incomplete vs cloud path
									</p>
									<p>
										<span className="text-slate-300">Pros:</span> local-first
										and fast when supported
									</p>
									<p>
										<span className="text-slate-300">Cons:</span> unsupported on
										many DreameHome-only devices
									</p>
								</div>
							</div>

							<div className="border border-white/5 rounded-xl p-4 space-y-2">
								<p className="text-slate-300 font-semibold">
									How Tasshack is used here
								</p>
								<p className="text-slate-500 text-xs leading-relaxed">
									This repo loads modules from{" "}
									<Code>D:\Dev\repos\tasshack_dreame_vacuum_ref</Code> at
									runtime (not vendored source). We bootstrap their protocol
									classes, then wrap them behind FastMCP tools + REST endpoints.
								</p>
								<div className="space-y-1 text-xs text-slate-500">
									<p>
										<span className="text-slate-300">Bridge:</span>{" "}
										<Code>src\dreame_mcp\client.py</Code> dynamically imports
										Tasshack protocol/map modules
									</p>
									<p>
										<span className="text-slate-300">Adapter:</span> converts
										low-level results into stable MCP/REST JSON responses
									</p>
									<p>
										<span className="text-slate-300">Reason:</span> reuse proven
										Dreame reverse-engineered logic, add agentic + web UI
										surface
									</p>
								</div>
							</div>
						</div>
					</>
				)}
			</div>
		</div>
	);
}
