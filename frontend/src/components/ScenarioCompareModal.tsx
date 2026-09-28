import React from 'react';
import { ScenarioComparisonResult, WhatIfScenario } from '../types/digital_twin';
import { 
  X, CheckCircle, AlertTriangle, TrendingDown, 
  TrendingUp, Clock, ShieldCheck, ArrowRight, Sparkles 
} from 'lucide-react';

interface ScenarioCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ScenarioComparisonResult | null;
  scenario: WhatIfScenario | null;
  onApplyLive: () => void;
}

export const ScenarioCompareModal: React.FC<ScenarioCompareModalProps> = ({
  isOpen,
  onClose,
  result,
  scenario,
  onApplyLive
}) => {
  if (!isOpen || !result || !scenario) return null;

  const isFaster = result.time_delta_minutes < 0;
  const absDeltaMin = Math.abs(result.time_delta_minutes);
  const absDeltaPct = Math.abs(result.time_delta_pct);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-slate-950/90 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-950 border border-indigo-700 text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white m-0">What-If Delta Analysis</h2>
              <p className="text-xs text-slate-400 m-0">Counterfactual Simulation vs Baseline</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scenario Details */}
        <div className="p-6 space-y-5">
          <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3.5">
            <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">
              Evaluated Scenario
            </div>
            <div className="text-sm font-bold text-slate-100">{scenario.title}</div>
            <p className="text-xs text-slate-400 mt-1 mb-0 leading-relaxed">
              {scenario.description}
            </p>
          </div>

          {/* Side-by-Side Key Metrics Comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Baseline Column */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Baseline Operations
              </div>
              <div>
                <div className="text-[11px] text-slate-400">Estimated Evacuation Time</div>
                <div className="text-2xl font-black text-slate-200">
                  {result.baseline_eet_minutes.toFixed(1)} <span className="text-xs font-normal text-slate-400">min</span>
                </div>
              </div>
              <div className="flex justify-between border-t border-slate-800/80 pt-2 text-xs">
                <span className="text-slate-400">Active Bottlenecks:</span>
                <span className="font-bold text-slate-200">{result.baseline_bottlenecks}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Pathogen Exposure:</span>
                <span className="font-bold text-slate-200">{(result.baseline_exposure_index * 100).toFixed(0)}%</span>
              </div>
            </div>

            {/* What-If Column */}
            <div className={`border rounded-xl p-4 space-y-3 ${
              isFaster ? 'bg-emerald-950/30 border-emerald-500/50' : 'bg-amber-950/30 border-amber-500/50'
            }`}>
              <div className="text-xs font-bold uppercase tracking-wider flex items-center justify-between">
                <span className={isFaster ? 'text-emerald-400' : 'text-amber-400'}>
                  What-If Strategy
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-black flex items-center gap-1 ${
                  isFaster ? 'bg-emerald-900/80 text-emerald-300' : 'bg-amber-900/80 text-amber-300'
                }`}>
                  {isFaster ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
                  {isFaster ? `-${absDeltaPct}% TIME` : `+${absDeltaPct}% TIME`}
                </span>
              </div>
              <div>
                <div className="text-[11px] text-slate-400">Projected Evacuation Time</div>
                <div className={`text-2xl font-black ${isFaster ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {result.what_if_eet_minutes.toFixed(1)} <span className="text-xs font-normal text-slate-400">min</span>
                </div>
              </div>
              <div className="flex justify-between border-t border-slate-800/80 pt-2 text-xs">
                <span className="text-slate-400">Active Bottlenecks:</span>
                <span className={`font-bold ${result.what_if_bottlenecks <= result.baseline_bottlenecks ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {result.what_if_bottlenecks}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Pathogen Exposure:</span>
                <span className="font-bold text-slate-200">{(result.what_if_exposure_index * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* AI Tactical Recommendation Card */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-start gap-3">
            <div className={`p-2 rounded-lg shrink-0 ${isFaster ? 'bg-emerald-950 text-emerald-400' : 'bg-amber-950 text-amber-400'}`}>
              {isFaster ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
            </div>
            <div>
              <div className="text-xs font-bold text-slate-200 mb-0.5">
                AI Strategic Recommendation
              </div>
              <p className="text-xs text-slate-300 m-0 leading-relaxed">
                {result.recommendation}
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="bg-slate-950/90 px-6 py-4 border-t border-slate-800 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold rounded-xl transition-colors"
          >
            Close & Keep Baseline
          </button>
          <button
            onClick={() => {
              onApplyLive();
              onClose();
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg transition-all"
          >
            Deploy Intervention to Live Twin <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
