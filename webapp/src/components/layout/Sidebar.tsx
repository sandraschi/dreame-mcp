import { motion } from "framer-motion";
import {
	Activity,
	Bot,
	ChevronLeft,
	ChevronRight,
	HelpCircle,
	LayoutDashboard,
	PlayCircle,
	ScanLine,
	Settings,
	Wrench,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
	{ path: "/", label: "Dashboard", icon: LayoutDashboard },
	{ path: "/map", label: "LIDAR Map", icon: ScanLine },
	{ path: "/status", label: "Status", icon: Activity },
	{ path: "/controls", label: "Controls", icon: PlayCircle },
	{ path: "/tools", label: "MCP Tools", icon: Wrench },
	{ path: "/settings", label: "Settings", icon: Settings },
	{ path: "/help", label: "Help", icon: HelpCircle },
];

export default function Sidebar({
	isCollapsed,
	onToggle,
}: {
	isCollapsed: boolean;
	onToggle: () => void;
}) {
	return (
		<motion.aside
			initial={false}
			animate={{ width: isCollapsed ? 80 : 260 }}
			className="relative flex flex-col bg-[#0f0f12] border-r border-white/5 z-50 overflow-hidden"
		>
			<div className="h-20 flex items-center px-6 mb-4">
				<div className="flex items-center gap-4">
					<div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
						<Bot className="text-white w-6 h-6" />
					</div>
					{!isCollapsed && (
						<motion.div
							initial={{ opacity: 0 }}
							animate={{ opacity: 1 }}
							className="flex flex-col"
						>
							<span className="text-lg font-bold tracking-tight text-white leading-tight">
								DREAME D20
							</span>
							<span className="text-[10px] font-medium text-amber-400/80 uppercase tracking-widest">
								Mission Control
							</span>
						</motion.div>
					)}
				</div>
			</div>
			<nav className="flex-1 px-4 space-y-1.5 overflow-y-auto">
				{navItems.map((item) => (
					<NavLink
						key={item.path}
						to={item.path}
						className={({ isActive }) =>
							`flex items-center gap-4 px-3 py-3 rounded-xl transition-all duration-200 ${
								isActive
									? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
									: "text-slate-400 hover:bg-white/5 hover:text-slate-200 border border-transparent"
							}`
						}
					>
						<item.icon className="w-5 h-5 flex-shrink-0" />
						{!isCollapsed && (
							<span className="text-sm font-medium">{item.label}</span>
						)}
					</NavLink>
				))}
			</nav>
			<button
				type="button"
				onClick={onToggle}
				className="absolute -right-3 top-24 w-6 h-6 rounded-full bg-[#0f0f12] border border-white/10 flex items-center justify-center text-slate-500 hover:text-slate-300"
			>
				{isCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
			</button>
		</motion.aside>
	);
}
