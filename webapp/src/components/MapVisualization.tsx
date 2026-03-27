import { motion } from 'framer-motion'
import { Map as MapIcon, Navigation, Crosshair } from 'lucide-react'

export interface MapPoint {
    x: number;
    y: number;
    type?: 'wall' | 'obstacle' | 'path';
}

interface MapProps {
    points?: MapPoint[];
    currentPos?: { x: number; y: number; heading: number };
}

export default function MapVisualization({ points = [], currentPos }: MapProps) {
    return (
        <div className="map-container rounded-2xl border border-white/5 relative bg-slate-950 overflow-hidden shadow-inner h-full min-h-[400px]">
            <div className="absolute inset-0 map-grid opacity-20" />

            {/* HUD Info */}
            <div className="absolute top-4 left-4 z-10 flex gap-2">
                <div className="glass-card px-3 py-1.5 rounded-lg flex items-center gap-2 text-xs text-slate-400">
                    <MapIcon size={14} className="text-indigo-400" />
                    <span>LIVE OCCUPANCY</span>
                </div>
                <div className="glass-card px-3 py-1.5 rounded-lg flex items-center gap-2 text-xs text-slate-400">
                    <Crosshair size={14} className="text-emerald-400" />
                    <span>SLAM ACTIVE</span>
                </div>
            </div>

            {/* Map Content */}
            <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative w-full h-full p-8">
                    {/* Mock Map Shapes */}
                    <motion.svg
                        viewBox="0 0 100 100"
                        className="w-full h-full drop-shadow-[0_0_15px_rgba(99,102,241,0.2)]"
                    >
                        <defs>
                            <radialGradient id="robotGlow">
                                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.6" />
                                <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                            </radialGradient>
                        </defs>

                        {/* Walls */}
                        <path
                            d="M10,10 L90,10 L90,90 L10,90 Z M30,30 L70,30 L70,70 L30,70 Z"
                            fill="none"
                            stroke="rgba(255,255,255,0.1)"
                            strokeWidth="0.5"
                            strokeDasharray="2 2"
                        />

                        {/* Robot Marker */}
                        <motion.g
                            animate={{
                                x: currentPos?.x || 50,
                                y: currentPos?.y || 50,
                                rotate: currentPos?.heading || 0
                            }}
                            transition={{ type: 'spring', damping: 20 }}
                        >
                            <circle r="6" fill="url(#robotGlow)" />
                            <circle r="2" fill="#3b82f6" stroke="white" strokeWidth="0.5" />
                            <path d="M0,-2 L2,2 L-2,2 Z" fill="white" transform="translate(0, -4)" />
                        </motion.g>
                    </motion.svg>
                </div>
            </div>

            {/* Compass Overlay */}
            <div className="absolute bottom-4 right-4 glass-card p-3 rounded-full">
                <Navigation size={20} className="text-slate-400" style={{ transform: `rotate(${(currentPos?.heading || 0)}deg)` }} />
            </div>
        </div>
    )
}
