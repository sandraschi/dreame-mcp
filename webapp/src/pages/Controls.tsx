import {
	AlertCircle,
	Home,
	Loader2,
	MapPin,
	PlayCircle,
	Square,
} from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";

const commands = [
	{ id: "start_clean", label: "Start cleaning", icon: PlayCircle },
	{ id: "stop", label: "Stop", icon: Square },
	{ id: "pause", label: "Pause", icon: Square },
	{ id: "go_home", label: "Return to dock", icon: Home },
	{ id: "find_robot", label: "Find robot", icon: MapPin },
] as const;

export default function Controls() {
	const [loading, setLoading] = useState<string | null>(null);
	const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(
		null,
	);

	const send = async (cmd: string) => {
		setLoading(cmd);
		setMsg(null);
		try {
			await api.control(cmd);
			setMsg({ type: "ok", text: `Sent ${cmd}` });
		} catch (e) {
			setMsg({ type: "err", text: e instanceof Error ? e.message : "Failed" });
		} finally {
			setLoading(null);
		}
	};

	return (
		<div className="space-y-6 py-4 max-w-4xl">
			<div className="flex items-center gap-4">
				<PlayCircle className="text-amber-400 w-8 h-8" />
				<div>
					<h1 className="text-2xl font-bold text-white tracking-tight">
						Controls
					</h1>
					<p className="text-slate-400 text-sm">
						Start, stop, pause, return to dock. Requires DREAME_IP and
						DREAME_TOKEN (miio).
					</p>
				</div>
			</div>

			{msg && (
				<div
					className={`flex items-center gap-3 p-4 rounded-2xl border ${
						msg.type === "ok"
							? "border-green-500/20 bg-green-500/10 text-green-200"
							: "border-amber-500/20 bg-amber-500/10 text-amber-200"
					}`}
				>
					{msg.type === "err" && (
						<AlertCircle className="w-5 h-5 flex-shrink-0" />
					)}
					<p className="text-sm">{msg.text}</p>
				</div>
			)}

			<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
				{commands.map((c) => (
					<button
						type="button"
						key={c.id}
						onClick={() => send(c.id)}
						disabled={loading !== null}
						className="flex items-center gap-4 p-5 rounded-2xl border border-white/10 bg-[#0f0f12]/80 hover:border-amber-500/30 hover:bg-amber-500/10 disabled:opacity-50 transition-all"
					>
						{loading === c.id ? (
							<Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
						) : (
							<c.icon className="w-6 h-6 text-amber-400" />
						)}
						<span className="text-sm font-medium text-slate-200">
							{c.label}
						</span>
					</button>
				))}
			</div>
		</div>
	);
}
