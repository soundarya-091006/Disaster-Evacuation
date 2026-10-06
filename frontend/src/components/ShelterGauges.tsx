import React from 'react';
import { ShelterHospital } from '../types/digital_twin';
import { Hospital, ShieldCheck, AlertCircle, Users, Activity } from 'lucide-react';

interface ShelterGaugesProps {
  shelters: ShelterHospital[];
}

export const ShelterGauges: React.FC<ShelterGaugesProps> = ({ shelters }) => {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 backdrop-blur-md shadow-md flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-teal-950 border border-teal-800 text-teal-400">
            <Hospital className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 m-0">Shelters & Quarantine Facilities</h2>
            <p className="text-[11px] text-slate-400 m-0">Live bed intake & capacity monitoring</p>
          </div>
        </div>

        <div className="text-[11px] text-slate-400">
          <span className="font-bold text-teal-400">{shelters.length}</span> Active Facilities
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {shelters.map((s) => {
          const occPct = (s.occupied / Math.max(s.total_capacity, 1)) * 100;
          const isQuarantine = s.type === 'hospital_quarantine';
          const isFull = occPct >= 95;
          const isNear = occPct >= 80 && !isFull;

          return (
            <div
              key={s.id}
              className={`p-3 rounded-xl border transition-all ${
                isFull
                  ? 'bg-rose-950/40 border-rose-800/80 shadow-sm'
                  : isNear
                  ? 'bg-amber-950/40 border-amber-800/80'
                  : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="truncate">
                  <div className="text-xs font-bold text-slate-200 truncate">{s.name}</div>
                  <div className="text-[10px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <span className="capitalize">{s.type.replace('_', ' ')}</span>
                    <span>•</span>
                    <span className="text-teal-400 font-medium">{s.intake_rate_per_min} /min intake</span>
                  </div>
                </div>

                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-black tracking-wider uppercase shrink-0 ${
                    isFull
                      ? 'bg-rose-900 text-rose-200 border border-rose-700'
                      : isNear
                      ? 'bg-amber-900 text-amber-200 border border-amber-700'
                      : 'bg-teal-950 text-teal-300 border border-teal-800'
                  }`}
                >
                  {isFull ? 'FULL' : isNear ? 'NEAR CAP' : 'OPEN'}
                </span>
              </div>

              {/* General Capacity Bar */}
              <div className="space-y-1 mb-2">
                <div className="flex justify-between text-[10px]">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Users className="w-3 h-3 text-slate-400" /> General Beds
                  </span>
                  <span className="font-bold text-slate-300">
                    {s.occupied} / {s.total_capacity} ({occPct.toFixed(0)}%)
                  </span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      isFull ? 'bg-rose-500' : isNear ? 'bg-amber-500' : 'bg-teal-400'
                    }`}
                    style={{ width: `${Math.min(100, occPct)}%` }}
                  />
                </div>
              </div>

              {/* Quarantine & Isolation Beds (if available) */}
              {s.quarantine_beds_total > 0 && (
                <div className="space-y-1 border-t border-slate-800/80 pt-1.5">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-rose-400 flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3 text-rose-400" /> Isolation Units
                    </span>
                    <span className="font-bold text-rose-300">
                      {s.quarantine_beds_occupied} / {s.quarantine_beds_total}
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                    <div
                      className="bg-rose-500 h-1 rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.min(100, (s.quarantine_beds_occupied / s.quarantine_beds_total) * 100)}%`
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
