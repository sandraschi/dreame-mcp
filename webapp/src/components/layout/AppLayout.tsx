import { AnimatePresence, motion } from "framer-motion";
import type React from "react";
import { useState } from "react";
import Sidebar from "./Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
	const [isCollapsed, setIsCollapsed] = useState(false);
	return (
		<div className="flex w-screen h-screen bg-[#0a0a0c] text-slate-200 overflow-hidden font-sans">
			<Sidebar
				isCollapsed={isCollapsed}
				onToggle={() => setIsCollapsed(!isCollapsed)}
			/>
			<main className="flex-1 flex flex-col overflow-hidden bg-[#0a0a0c] relative">
				<div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-600/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none" />
				<div className="flex-1 overflow-y-auto relative z-10 p-6 lg:p-10 w-full">
					<AnimatePresence mode="wait">
						<motion.div
							key={window.location.pathname}
							initial={{ opacity: 0, y: 10 }}
							animate={{ opacity: 1, y: 0 }}
							exit={{ opacity: 0, y: -10 }}
							transition={{ duration: 0.2 }}
							className="max-w-7xl mx-auto w-full"
						>
							{children}
						</motion.div>
					</AnimatePresence>
				</div>
			</main>
		</div>
	);
}
