import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Play, Square, Home, Target, Zap,
    Battery, Wind, Clock, AreaChart, Settings,
    AlertCircle, ChevronRight, Activity
} from 'lucide-react'
import MapVisualization from '../components/MapVisualization'

interface Telemetry {
    state: string;
    battery: number;
    fan_speed: string;
    is_charging: boolean;
    is_cleaning: boolean;
    cleaned_area: number;
    cleaning_time: number;
}

export default function MissionControl() {
    const [telemetry, setTelemetry] = useState<Telemetry | null>(null)
    const [isNavOpen, setIsNavOpen] = useState(true)

    // --- Real-time Gateway Sync ---
    const GATEWAY_URL = 'http://localhost:10725'

    useEffect(() => {
        const poll = async () => {
            try {
                const res = await fetch(`${GATEWAY_URL}/api/v1/telemetry`)
                if (res.ok) {
                    const data = await res.json()
                    setTelemetry(data)
                }
            } catch (err) {
                // Fallback or Mock
                setTelemetry({
                    state: "Docked (Mock)",
                    battery: 89,
                    fan_speed: "Standard",
                    is_charging: true,
                    is_cleaning: false,
                    cleaned_area: 42.8,
                    cleaning_time: 2150
                })
            }
        }
        const interval = setInterval(poll, 2000)
        poll()
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="flex h-screen bg-[#05070a] text-slate-100 overflow-hidden">
            {/* Side Navigation */}
            <motion.aside
                initial={false}
                animate={{ width: isNavOpen ? 260 : 80 }}
                className="glass-card border-y-0 border-l-0 border-r-white/5 flex flex-col z-20"
            >
                <div className="p-6 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                        <Zap className="text-white fill-white" size={20} />
                    </div>
                    {isNavOpen && <span className="font-bold tracking-tight text-lg">DREAME-MCP</span>}
                </div>

                <nav className="flex-1 px-4 space-y-2 py-4">
                    <NavButton icon={<Activity size={20} />} label="Dashboard" active collapsed={!isNavOpen} />
                    <NavButton icon={<Clock size={20} />} label="Schedules" collapsed={!isNavOpen} />
                    <NavButton icon={<Settings size={20} />} label="Settings" collapsed={!isNavOpen} />
                </nav>
            </motion.aside>

            {/* Main Mission Control */}
            <main className="flex-1 overflow-y-auto relative p-8">
                <div className="sota-glow -top-40 -right-40" />

                {/* Header Stats */}
                <header className="flex items-center justify-between mb-8">
                    <div className="animate-fade-in">
                        <h1 className="text-3xl font-extrabold tracking-tight mb-1">Mission Control</h1>
                        <p className="text-slate-400 text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                            SYSTEM OPERATIONAL - V8.4.1 (FAST-MCP 3.1)
                        </p>
                    </div>

                    <div className="flex gap-4">
                        <StatCard icon={<Battery className="text-emerald-400" size={16} />} label="Battery" value={`${telemetry?.battery}%`} />
                        <StatCard icon={<Clock className="text-indigo-400" size={16} />} label="Runtime" value={`${Math.floor((telemetry?.cleaning_time || 0) / 60)}m`} />
                        <StatCard icon={<AreaChart className="text-sky-400" size={16} />} label="Area" value={`${telemetry?.cleaned_area}m²`} />
                    </div>
                </header>

                {/* Content Grid */}
                <div className="grid grid-cols-12 gap-6">
                    {/* Map View */}
                    <section className="col-span-12 xl:col-span-8 h-[600px] animate-fade-in opacity-0" style={{ animationDelay: '0.1s' }}>
                        <MapVisualization />
                    </section>

                    {/* Controls & Health */}
                    <section className="col-span-12 xl:col-span-4 space-y-6">
                        {/* Command Center */}
                        <div className="glass-card rounded-2xl p-6 animate-fade-in opacity-0" style={{ animationDelay: '0.2s' }}>
                            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6">Execution Suite</h2>
                            <div className="grid grid-cols-2 gap-4">
                                <ControlButton icon={<Play size={20} />} label="START" variant="primary" />
                                <ControlButton icon={<Square size={20} />} label="STOP" variant="secondary" />
                                <ControlButton icon={<Home size={20} />} label="DOCK" variant="outline" />
                                <ControlButton icon={<Target size={20} />} label="ZONE" variant="outline" />
                            </div>
                        </div>

                        {/* Maintenance Status */}
                        <div className="glass-card rounded-2xl p-6 animate-fade-in opacity-0" style={{ animationDelay: '0.3s' }}>
                            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Component Health</h2>
                            <div className="space-y-4">
                                <HealthBar label="Main Brush" percent={82} />
                                <HealthBar label="Side Brush" percent={45} warning />
                                <HealthBar label="Filter Unit" percent={91} />
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    )
}

function NavButton({ icon, label, active = false, collapsed = false }: any) {
    return (
        <button className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${active ? 'bg-indigo-600/10 text-indigo-400' : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'}`}>
            {icon}
            {!collapsed && <span className="font-medium">{label}</span>}
        </button>
    )
}

function StatCard({ icon, label, value }: any) {
    return (
        <div className="glass-card px-4 py-3 rounded-2xl min-w-[120px]">
            <div className="flex items-center gap-2 mb-1">
                {icon}
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-xl font-bold font-mono">{value}</div>
        </div>
    )
}

function ControlButton({ icon, label, variant }: any) {
    const styles: any = {
        primary: "bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/20 text-white",
        secondary: "bg-slate-800 hover:bg-slate-700 text-slate-200",
        outline: "bg-transparent border border-white/10 hover:bg-white/5 text-slate-400 hover:text-slate-200"
    }
    return (
        <button className={`flex flex-col items-center justify-center py-4 rounded-xl transition-all gap-2 ${styles[variant]}`}>
            {icon}
            <span className="text-[10px] font-extrabold tracking-tighter">{label}</span>
        </button>
    )
}

function HealthBar({ label, percent, warning }: any) {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between text-[10px] font-bold">
                <span className="text-slate-400">{label}</span>
                <span className={warning ? 'text-amber-400' : 'text-indigo-400'}>{percent}%</span>
            </div>
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${percent}%` }}
                    className={`h-full ${warning ? 'bg-amber-500' : 'bg-indigo-500'}`}
                />
            </div>
        </div>
    )
}
