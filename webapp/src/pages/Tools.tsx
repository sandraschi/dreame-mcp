import { Check, Copy, Wrench } from "lucide-react";
import { useState } from "react";

const Code = ({ children }: { children: string }) => {
	const [copied, setCopied] = useState(false);
	const copy = () => {
		navigator.clipboard.writeText(children);
		setCopied(true);
		setTimeout(() => setCopied(false), 1500);
	};
	return (
		<div className="relative group mt-2">
			<pre className="bg-black/60 border border-white/10 rounded-xl px-4 py-3 text-xs text-slate-300 font-mono overflow-x-auto whitespace-pre-wrap break-all">
				{children}
			</pre>
			<button
				type="button"
				onClick={copy}
				className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg bg-white/10 hover:bg-white/20"
			>
				{copied ? (
					<Check size={12} className="text-green-400" />
				) : (
					<Copy size={12} className="text-slate-400" />
				)}
			</button>
		</div>
	);
};

export default function Tools() {
	return (
		<div className="space-y-6 py-4 max-w-4xl">
			<div className="flex items-center gap-4">
				<Wrench className="text-amber-400 w-8 h-8" />
				<div>
					<h1 className="text-2xl font-bold text-white tracking-tight">
						MCP Tools
					</h1>
					<p className="text-slate-400 text-sm">
						Dreame D20 Pro tools for AI clients (Cursor, Claude Desktop)
					</p>
				</div>
			</div>
			<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5 space-y-4">
				<p className="text-sm text-slate-400">
					Connect your MCP client to{" "}
					<code className="text-amber-400">http://localhost:10794/sse</code>{" "}
					(SSE transport).
				</p>
				<div>
					<p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
						Portmanteau
					</p>
					<p className="text-sm text-slate-400">
						dreame(operation=&quot;status&quot;),
						dreame(operation=&quot;map&quot;),
						dreame(operation=&quot;start_clean&quot;),
						dreame(operation=&quot;stop&quot;),
						dreame(operation=&quot;go_home&quot;),
						dreame(operation=&quot;find_robot&quot;),
						dreame(operation=&quot;battery&quot;)
					</p>
				</div>
				<div>
					<p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
						Help
					</p>
					<p className="text-sm text-slate-400">
						dreame_help(category=...) — categories: status, map, control,
						connection
					</p>
				</div>
				<div>
					<p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
						Agentic workflow (SEP-1577)
					</p>
					<p className="text-sm text-slate-400">
						dreame_agentic_workflow(goal=&quot;...&quot;) — LLM plans and runs
						get_status, get_map, start_clean, stop, go_home, find_robot
					</p>
				</div>
				<div>
					<p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">
						mcp_config.json
					</p>
					<Code>{`{
  "mcpServers": {
    "dreame": {
      "url": "http://localhost:10794/sse",
      "transport": "sse"
    }
  }
}`}</Code>
				</div>
			</div>
		</div>
	);
}
