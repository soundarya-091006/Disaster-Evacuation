import React from 'react';
import { PredictionHorizonData } from '../types/digital_twin';
import { Clock, TrendingUp, AlertCircle, ShieldCheck, Gauge } from 'lucide-react';

interface PredictionHorizonProps {
  selectedHorizon: 'now' | '15m' | '30m' | '60m';
  onSelectHorizon: (h: 'now' | '15m' | '30m' | '60m') => void;
  predictions: Record<string, PredictionHorizonData> | undefined;
}

export const PredictionHorizon: React.FC<PredictionHorizonProps> = ({
  selectedHorizon,
  onSelectHorizon,
  predictions
}) => {
  const currentPred = selectedHorizon !== 'now' ? predictions?.[selectedHorizon] : null;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 backdrop-blur-md shadow-md">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Predictive Timeline Scrubber
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono">
            Sequential AI / LSTM
          </span>
        </div>

        {currentPred && (
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{currentPred.confidence_pct}% Model Confidence</span>
          </div>
        )}
      </div>

      {/* Horizon Selector Tabs */}
      <div className="grid grid-cols-4 gap-2 mb-2.5">
        {[
          { key: 'now', label: 'NOW', sub: 'Real-time Twin' },
          { key: '15m', label: '+15 MIN', sub: 'Surge Horizon' },
          { key: '30m', label: '+30 MIN', sub: 'Peak Jam Horizon' },
          { key: '60m', label: '+60 MIN', sub: 'System Cleared?' }
        ].map((item) => {
          const isSelected = selectedHorizon === item.key;
          return (
            <button
              key={item.key}
              onClick={() => onSelectHorizon(item.key as any)}
              className={`flex flex-col items-center justify-center py-2 px-2 rounded-lg border text-center transition-all ${
                isSelected
                  ? 'bg-cyan-950/80 border-cyan-500/80 text-cyan-300 shadow-md ring-1 ring-cyan-500/30'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
              }`}
            >
              <span className={`text-xs font-black tracking-wide ${isSelected ? 'text-cyan-300' : 'text-slate-300'}`}>
                {item.label}
              </span>
              <span className="text-[10px] text-slate-500 font-medium mt-0.5">
                {item.sub}
              </span>
            </button>
          );
        })}
      </div>

      {/* Forecast Metric Summary Strip */}
      {currentPred ? (
        <div className="grid grid-cols-3 gap-2 bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            <div>
              <div className="text-[10px] text-slate-400">Forecasted Congestion</div>
              <div className="text-xs font-bold text-cyan-300">
                {currentPred.predicted_network_congestion_pct}% network
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <div>
              <div className="text-[10px] text-slate-400">Impending Bottlenecks</div>
              <div className="text-xs font-bold text-amber-300">
                {currentPred.predicted_congested_road_count} road segments
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-emerald-400" />
            <div>
              <div className="text-[10px] text-slate-400">Projected Avg Speed</div>
              <div className="text-xs font-bold text-emerald-300">
                {currentPred.predicted_average_speed_kmh} km/h
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-[11px] text-slate-400 flex items-center justify-between bg-slate-950/50 rounded-lg px-3 py-1.5 border border-slate-800/60">
          <span>Displaying live sensor & agent mobility state.</span>
          <span className="text-cyan-400 font-medium">Click +15m / +30m to project future state</span>
        </div>
      )}
    </div>
  );
};
