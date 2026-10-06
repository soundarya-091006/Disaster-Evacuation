import React from 'react';
import { TacticalAdvisory, AnomalyReport } from '../types/digital_twin';
import { ShieldAlert, AlertTriangle, CheckCircle, Radio, Sparkles, Navigation } from 'lucide-react';

interface AdvisoryFeedProps {
  advisories: TacticalAdvisory[];
  anomalies: AnomalyReport[];
}

export const AdvisoryFeed: React.FC<AdvisoryFeedProps> = ({ advisories, anomalies }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 backdrop-blur-md shadow-md flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 m-0">AI Evacuation Dispatch Advisories</h2>
            <p className="text-[11px] text-slate-400 m-0">Real-time dynamic tactical routing suggestions</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[11px] text-cyan-400 font-mono">
          <Radio className="w-3.5 h-3.5 animate-pulse" />
          <span>AUTONOMOUS DISPATCH</span>
        </div>
      </div>

      {/* Advisory list */}
      <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
        {advisories.length === 0 && anomalies.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-center text-xs text-slate-400">
            <CheckCircle className="w-5 h-5 text-emerald-400 mx-auto mb-1.5" />
            Corridors operating within safe impedance limits. No rerouting needed.
          </div>
        ) : (
          <>
            {/* Anomalies first */}
            {anomalies.map((anom) => (
              <div
                key={anom.id}
                className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/80 flex items-start gap-2.5"
              >
                <div className="p-1 rounded bg-rose-900/80 text-rose-200 mt-0.5 shrink-0">
                  <ShieldAlert className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs font-bold text-rose-200">
                    <span>{anom.anomaly_type.replace('_', ' ')}</span>
                    <span className="text-[10px] text-rose-400 font-mono">T+{anom.timestamp_sim_min}m</span>
                  </div>
                  <div className="text-[11px] text-slate-300 font-medium mt-0.5">{anom.location}</div>
                  <p className="text-[10px] text-slate-400 mt-1 m-0 leading-relaxed">
                    {anom.description}
                  </p>
                </div>
              </div>
            ))}

            {/* Tactical Advisories */}
            {advisories.map((adv) => (
              <div
                key={adv.id}
                className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 flex items-start gap-2.5 transition-all"
              >
                <div className="p-1 rounded bg-amber-950 border border-amber-800 text-amber-300 mt-0.5 shrink-0">
                  <Navigation className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-200">
                    <span>{adv.title}</span>
                    <span className="text-[10px] text-cyan-400 font-mono">T+{adv.timestamp_sim_min}m</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 m-0 leading-relaxed">
                    {adv.message}
                  </p>
                  <div className="mt-2 flex items-center justify-between text-[10px]">
                    <span className="text-emerald-400 font-medium">
                      Action: {adv.recommended_action}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 font-bold uppercase">
                      AUTO-DISPATCHED
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
};
