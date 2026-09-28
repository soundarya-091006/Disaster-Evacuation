import React from 'react';
import { SimulationStepState } from '../types/digital_twin';
import { 
  Play, Pause, StepForward, RotateCcw, 
  Radio, Clock, AlertTriangle, Users, 
  Activity, ShieldAlert, FileText, Zap
} from 'lucide-react';

interface TelemetryHeaderProps {
  state: SimulationStepState | null;
  isConnected: boolean;
  onStart: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onSetSpeed: (speed: number) => void;
  onOpenReportModal: () => void;
}

export const TelemetryHeader: React.FC<TelemetryHeaderProps> = ({
  state,
  isConnected,
  onStart,
  onPause,
  onStep,
  onReset,
  onSetSpeed,
  onOpenReportModal
}) => {
  const isRunning = state?.is_running ?? false;
  const speed = state?.speed_multiplier ?? 1.0;

  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-40 shadow-lg">
      {/* Brand & Incident Scope */}
      <div className="flex items-center gap-3">
        <div className="bg-gradient-to-tr from-cyan-600 to-blue-500 p-2.5 rounded-xl shadow-md flex items-center justify-center text-white ring-1 ring-cyan-400/30">
          <Zap className="w-5 h-5 text-cyan-200" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-white m-0">TWINEVAC</h1>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              Digital Twin v2.4
            </span>
            <div className="flex items-center gap-1.5 ml-1">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-xs text-slate-400">{isConnected ? 'Live Telemetry' : 'Disconnected'}</span>
            </div>
          </div>
          <p className="text-xs text-slate-400 m-0">
            Salem District Incident Command & Evacuation Operations Center
          </p>
        </div>
      </div>

      {/* Key Operational KPIs */}
      <div className="flex items-center gap-3">
        {/* EET KPI */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-1.5 min-w-[130px]">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-0.5">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3 text-cyan-400" /> Est. Evac Time</span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-black text-cyan-400">
              {state?.estimated_evacuation_time_minutes ?? 0}
            </span>
            <span className="text-xs text-slate-400 font-medium">min</span>
            {state && (
              <span className="text-[10px] font-semibold text-emerald-400 ml-auto">
                -{Math.max(0, (state.baseline_eet_minutes ?? 0) - (state.estimated_evacuation_time_minutes ?? 0)).toFixed(0)}m opt
              </span>
            )}
          </div>
        </div>

        {/* Evacuation Progress KPI */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-1.5 min-w-[140px]">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-0.5">
            <span className="flex items-center gap-1"><Users className="w-3 h-3 text-blue-400" /> Cleared Pop</span>
            <span className="text-[11px] font-bold text-slate-300">{state?.evacuation_progress_pct ?? 0}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 my-1 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-emerald-400 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, state?.evacuation_progress_pct ?? 0)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 flex justify-between">
            <span>{state?.total_evacuated.toLocaleString() ?? 0}</span>
            <span>/ {state?.total_at_risk_population.toLocaleString() ?? 0}</span>
          </div>
        </div>

        {/* Bottlenecks KPI */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-1.5 min-w-[110px]">
          <div className="text-[11px] text-slate-400 mb-0.5 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" /> Bottlenecks
          </div>
          <div className="text-xl font-black text-amber-400">
            {state?.active_bottlenecks_count ?? 0}
            <span className="text-xs text-slate-400 font-normal ml-1">chokes</span>
          </div>
        </div>

        {/* In-Transit Count */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg px-3.5 py-1.5 min-w-[110px]">
          <div className="text-[11px] text-slate-400 mb-0.5 flex items-center gap-1">
            <Activity className="w-3 h-3 text-emerald-400" /> In Transit
          </div>
          <div className="text-xl font-black text-slate-200">
            {state?.total_in_transit.toLocaleString() ?? 0}
            <span className="text-xs text-slate-400 font-normal ml-1">people</span>
          </div>
        </div>
      </div>

      {/* Control Buttons & Report Actions */}
      <div className="flex items-center gap-2">
        {/* Sim Elapsed Time Badge */}
        <div className="px-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-xs font-mono text-cyan-300 flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>T+ {(state?.elapsed_sim_minutes ?? 0).toFixed(1)}m</span>
        </div>

        {/* Speed Controls */}
        <div className="flex bg-slate-950 border border-slate-800 rounded-lg p-0.5">
          {[1, 2, 5].map((spd) => (
            <button
              key={spd}
              onClick={() => onSetSpeed(spd)}
              className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                speed === spd
                  ? 'bg-cyan-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>

        {/* Play/Pause Button */}
        {isRunning ? (
          <button
            onClick={onPause}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600/90 hover:bg-amber-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all"
            title="Pause Simulation"
          >
            <Pause className="w-3.5 h-3.5" /> Pause
          </button>
        ) : (
          <button
            onClick={onStart}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all"
            title="Start Simulation"
          >
            <Play className="w-3.5 h-3.5 fill-current" /> Run Twin
          </button>
        )}

        {/* Step Forward Button */}
        <button
          onClick={onStep}
          disabled={isRunning}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 rounded-lg border border-slate-700 transition-colors"
          title="Step Forward (+0.5 min)"
        >
          <StepForward className="w-4 h-4" />
        </button>

        {/* Reset Button */}
        <button
          onClick={onReset}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
          title="Reset to Initial Baseline"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        {/* Export Report Button */}
        <button
          onClick={onOpenReportModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/90 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg shadow-sm transition-all ml-1"
        >
          <FileText className="w-3.5 h-3.5" /> Export Audit
        </button>
      </div>
    </header>
  );
};
