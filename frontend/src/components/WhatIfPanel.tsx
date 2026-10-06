import React, { useState } from 'react';
import { WhatIfScenario, ScenarioComparisonResult, RoadSegment } from '../types/digital_twin';
import { 
  Sliders, Play, RotateCcw, AlertTriangle, 
  Sparkles, Check, ArrowRight, ShieldBan, 
  Hospital, Waves, Bus
} from 'lucide-react';

interface WhatIfPanelProps {
  roads: RoadSegment[];
  activeScenario: WhatIfScenario | null;
  onEvaluateScenario: (scenario: WhatIfScenario) => Promise<void>;
  onApplyScenario: (scenario: WhatIfScenario) => Promise<void>;
  onClearScenario: () => Promise<void>;
  isEvaluating: boolean;
}

const PREDEFINED_SCENARIOS: WhatIfScenario[] = [
  {
    scenario_id: 'SCENARIO_SHEVAPET_LOCKDOWN',
    title: 'Shevapet Red-Zone Contagion Lockdown & River Flood',
    description: 'Strict containment cordon around Shevapet bazaar. Blocks central access road and diverts crowds to Steel Plant bypass.',
    closed_road_ids: ['EDGE_4ROADS_SHEVAPET', 'EDGE_SHEVAPET_GUGAI'],
    shelter_capacity_multipliers: { SHELTER_GMKMC: 1.0, SHELTER_STEEL_PLANT: 1.25 },
    hazard_radius_multiplier: 1.35,
    evacuation_speed_multiplier: 1.0,
    quarantine_lockdown_zone_ids: ['ZONE_SHEVAPET']
  },
  {
    scenario_id: 'SCENARIO_GMKMC_OVERFLOW',
    title: 'GMKMC Hospital 100% Saturation (Triage Redirect)',
    description: 'GMKMC reaches maximum quarantine capacity. Reroutes ambulances and patients to Steel Plant and Gorimedu refuge.',
    closed_road_ids: [],
    shelter_capacity_multipliers: { SHELTER_GMKMC: 0.4 },
    hazard_radius_multiplier: 1.0,
    evacuation_speed_multiplier: 1.0,
    quarantine_lockdown_zone_ids: []
  },
  {
    scenario_id: 'SCENARIO_FOUR_ROADS_CHOKE',
    title: 'Salem 4-Roads Arterial Gridlock & Flash Inundation',
    description: 'Simulates flash inundation blocking 4-Roads junction, forcing traffic rerouting across outer ring roads.',
    closed_road_ids: ['EDGE_MEYYANUR_4ROADS', 'EDGE_4ROADS_COLLECT'],
    shelter_capacity_multipliers: {},
    hazard_radius_multiplier: 1.2,
    evacuation_speed_multiplier: 0.85,
    quarantine_lockdown_zone_ids: []
  },
  {
    scenario_id: 'SCENARIO_EXPRESS_TRANSIT',
    title: 'Deployment of 50 Express Evacuation Buses',
    description: 'Deploys high-capacity emergency transit on National Highway bypass corridors, expanding clearance throughput.',
    closed_road_ids: [],
    shelter_capacity_multipliers: { SHELTER_STEEL_PLANT: 1.3, SHELTER_AYODHYA: 1.2 },
    hazard_radius_multiplier: 0.9,
    evacuation_speed_multiplier: 1.5,
    quarantine_lockdown_zone_ids: []
  }
];

export const WhatIfPanel: React.FC<WhatIfPanelProps> = ({
  roads,
  activeScenario,
  onEvaluateScenario,
  onApplyScenario,
  onClearScenario,
  isEvaluating
}) => {
  const [selectedPresetId, setSelectedPresetId] = useState<string>(PREDEFINED_SCENARIOS[0].scenario_id);
  const [hazardMultiplier, setHazardMultiplier] = useState<number>(1.2);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1.0);
  const [selectedRoadsToClose, setSelectedRoadsToClose] = useState<string[]>(['EDGE_4ROADS_SHEVAPET']);

  const getScenarioToRun = (): WhatIfScenario => {
    const preset = PREDEFINED_SCENARIOS.find(s => s.scenario_id === selectedPresetId);
    if (preset) {
      return {
        ...preset,
        hazard_radius_multiplier: hazardMultiplier,
        evacuation_speed_multiplier: speedMultiplier
      };
    }
    return {
      scenario_id: 'CUSTOM_WHAT_IF',
      title: 'Custom Emergency Intervention',
      description: 'Operator configured interventions',
      closed_road_ids: selectedRoadsToClose,
      shelter_capacity_multipliers: {},
      hazard_radius_multiplier: hazardMultiplier,
      evacuation_speed_multiplier: speedMultiplier,
      quarantine_lockdown_zone_ids: []
    };
  };

  const handleSelectPreset = (scenario: WhatIfScenario) => {
    setSelectedPresetId(scenario.scenario_id);
    setSelectedRoadsToClose(scenario.closed_road_ids);
    setHazardMultiplier(scenario.hazard_radius_multiplier);
    setSpeedMultiplier(scenario.evacuation_speed_multiplier);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 backdrop-blur-md shadow-md flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-400">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 m-0">What-If Simulation Sandbox</h2>
            <p className="text-[11px] text-slate-400 m-0">Test interventions before live deployment</p>
          </div>
        </div>

        {activeScenario && (
          <button
            onClick={onClearScenario}
            className="flex items-center gap-1 text-[11px] font-semibold text-rose-400 hover:text-rose-300 bg-rose-950/60 border border-rose-800 px-2 py-1 rounded-lg transition-colors"
          >
            <RotateCcw className="w-3 h-3" /> Clear Interventions
          </button>
        )}
      </div>

      {/* Preset Scenario Cards */}
      <div className="space-y-2">
        <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
          Select Disaster Scenario
        </label>
        <div className="grid grid-cols-1 gap-2">
          {PREDEFINED_SCENARIOS.map((sc) => {
            const isSelected = selectedPresetId === sc.scenario_id;
            return (
              <div
                key={sc.scenario_id}
                onClick={() => handleSelectPreset(sc)}
                className={`p-2.5 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-indigo-950/70 border-indigo-500 shadow-md ring-1 ring-indigo-500/40 text-slate-100'
                    : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    {sc.scenario_id.includes('SHEVAPET') && <ShieldBan className="w-3.5 h-3.5 text-rose-400" />}
                    {sc.scenario_id.includes('GMKMC') && <Hospital className="w-3.5 h-3.5 text-cyan-400" />}
                    {sc.scenario_id.includes('FOUR_ROADS') && <Waves className="w-3.5 h-3.5 text-amber-400" />}
                    {sc.scenario_id.includes('EXPRESS') && <Bus className="w-3.5 h-3.5 text-emerald-400" />}
                    {sc.title}
                  </span>
                  {isSelected && (
                    <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                  )}
                </div>
                <p className="text-[10px] text-slate-400 line-clamp-2 leading-relaxed m-0">
                  {sc.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sliders & Parameters */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-3 space-y-3">
        <div>
          <div className="flex justify-between text-[11px] text-slate-400 mb-1">
            <span>Hazard / Contagion Expansion Radius</span>
            <span className="font-mono text-cyan-400">{hazardMultiplier.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            min="0.8"
            max="2.0"
            step="0.05"
            value={hazardMultiplier}
            onChange={(e) => setHazardMultiplier(parseFloat(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>

        <div>
          <div className="flex justify-between text-[11px] text-slate-400 mb-1">
            <span>Evacuation Transit Flow Multiplier</span>
            <span className="font-mono text-cyan-400">{speedMultiplier.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={speedMultiplier}
            onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
            className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 pt-1">
        <button
          onClick={() => onEvaluateScenario(getScenarioToRun())}
          disabled={isEvaluating}
          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" />
          {isEvaluating ? 'Simulating Delta...' : 'Evaluate Delta'}
        </button>

        <button
          onClick={() => onApplyScenario(getScenarioToRun())}
          className="flex items-center justify-center gap-1.5 px-3 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-md transition-all"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          Apply to Live Twin
        </button>
      </div>
    </div>
  );
};
