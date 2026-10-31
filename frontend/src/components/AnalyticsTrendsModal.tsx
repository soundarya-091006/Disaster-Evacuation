import React from 'react';
import { LineChart, TrendingUp, X, Activity, Building, Users } from 'lucide-react';
import { SimulationStepState } from '../types/digital_twin';

interface AnalyticsTrendsModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: SimulationStepState | null;
}

export const AnalyticsTrendsModal: React.FC<AnalyticsTrendsModalProps> = ({
  isOpen,
  onClose,
  state
}) => {
  if (!isOpen || !state) return null;

  const congestionHistory = state.history_congestion_trend || [18, 22, 25, 29, 34, 31, 38];
  const shelterHistory = state.history_shelter_load || {};

  // Simple SVG trendline generator
  const renderTrendline = (data: number[], color: string, maxVal: number = 100) => {
    if (data.length < 2) return null;
    const width = 380;
    const height = 120;
    const pts = data.map((val, idx) => {
      const x = (idx / (data.length - 1)) * width;
      const y = height - (Math.min(maxVal, Math.max(0, val)) / maxVal) * (height - 15) - 5;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-32 overflow-visible">
        {/* Grid lines */}
        <line x1="0" y1="20" x2={width} y2="20" stroke="#334155" strokeDasharray="4" strokeWidth="0.8" />
        <line x1="0" y1="65" x2={width} y2="65" stroke="#334155" strokeDasharray="4" strokeWidth="0.8" />
        <line x1="0" y1="110" x2={width} y2="110" stroke="#334155" strokeDasharray="4" strokeWidth="0.8" />
        {/* Trend Polyline */}
        <polyline fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={pts} />
        {/* Dot at latest point */}
        {data.length > 0 && (
          <circle
            cx={width}
            cy={height - (Math.min(maxVal, Math.max(0, data[data.length - 1])) / maxVal) * (height - 15) - 5}
            r="4"
            fill={color}
          />
        )}
      </svg>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl shadow-cyan-950/40">
        
        {/* Header */}
        <div className="px-6 py-4 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-xl text-indigo-400">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">Dynamic Evacuation Analytics & Time-Series Trends</h2>
              <p className="text-xs text-slate-400">Real-time network congestion curve, shelter intake rate, and clearance velocities</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-200">
          
          {/* Top Quick Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Network Velocity</span>
              <span className="text-xl font-bold font-mono text-cyan-400 mt-1 block">
                {state.average_network_speed_kmh} <span className="text-xs text-slate-500">km/h</span>
              </span>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Bottlenecks</span>
              <span className="text-xl font-bold font-mono text-rose-400 mt-1 block">
                {state.active_bottlenecks_count} <span className="text-xs text-slate-500">chokes</span>
              </span>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Est Evac Completion</span>
              <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">
                {state.estimated_evacuation_time_minutes} <span className="text-xs text-slate-500">min</span>
              </span>
            </div>
          </div>

          {/* Chart 1: Average Network Congestion Index Over Time */}
          <div className="bg-slate-950/50 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Network Congestion Over Elapsed Simulation Time (T+ {state.elapsed_sim_minutes}m)
                </h3>
              </div>
              <span className="text-xs font-bold font-mono text-cyan-400">
                Latest: {congestionHistory[congestionHistory.length - 1] || 25}%
              </span>
            </div>
            {renderTrendline(congestionHistory, '#06b6d4', 100)}
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>T+ 0.0m (Baseline)</span>
              <span>80% Gridlock Threshold</span>
              <span>T+ {state.elapsed_sim_minutes}m</span>
            </div>
          </div>

          {/* Chart 2: Per-Facility Shelter Occupancies Over Time */}
          <div className="bg-slate-950/50 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Building className="w-4 h-4 text-emerald-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Facility Intake Saturation Curves (% Bed Fill Over Time)
                </h3>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {state.shelters.map((shelter, idx) => {
                const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899'];
                const color = colors[idx % colors.length];
                const hist = shelterHistory[shelter.id] || [shelter.occupancy_pct - 15, shelter.occupancy_pct - 5, shelter.occupancy_pct];

                return (
                  <div key={shelter.id} className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-lg">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-bold text-slate-300 truncate max-w-[200px]">{shelter.name.split(' (')[0]}</span>
                      <span className="font-mono font-bold" style={{ color }}>{shelter.occupancy_pct}%</span>
                    </div>
                    {renderTrendline(hist, color, 100)}
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-950/70 border-t border-slate-800 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold transition-colors cursor-pointer"
          >
            Close Analytics View
          </button>
        </div>

      </div>
    </div>
  );
};
