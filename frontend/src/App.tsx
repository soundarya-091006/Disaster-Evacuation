import React, { useState } from 'react';
import { useDigitalTwinSocket } from './hooks/useDigitalTwinSocket';
import { TelemetryHeader } from './components/TelemetryHeader';
import { PredictionHorizon } from './components/PredictionHorizon';
import { MapView } from './components/MapView';
import { WhatIfPanel } from './components/WhatIfPanel';
import { ShelterGauges } from './components/ShelterGauges';
import { AdvisoryFeed } from './components/AdvisoryFeed';
import { ScenarioCompareModal } from './components/ScenarioCompareModal';
import { ExportReportModal } from './components/ExportReportModal';
import { WhatIfScenario, ScenarioComparisonResult } from './types/digital_twin';

export const App: React.FC = () => {
  const {
    state,
    isConnected,
    isLoading,
    selectedHorizon,
    setSelectedHorizon,
    activeScenario,
    startSimulation,
    pauseSimulation,
    stepSimulation,
    resetSimulation,
    setSpeed,
    evaluateWhatIf,
    applyWhatIf,
    clearWhatIf
  } = useDigitalTwinSocket();

  // Modals state
  const [isCompareModalOpen, setIsCompareModalOpen] = useState<boolean>(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<ScenarioComparisonResult | null>(null);
  const [evaluatingScenario, setEvaluatingScenario] = useState<WhatIfScenario | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  // Road closure toggle handler
  const handleToggleRoadClosure = (roadId: string) => {
    if (!state) return;
    const isCurrentlyClosed = state.roads.find(r => r.id === roadId)?.is_closed;
    const updatedClosed = isCurrentlyClosed
      ? (activeScenario?.closed_road_ids || []).filter(id => id !== roadId)
      : [...(activeScenario?.closed_road_ids || []), roadId];

    const updatedScenario: WhatIfScenario = {
      scenario_id: activeScenario?.scenario_id || 'CUSTOM_CLOSURE',
      title: activeScenario?.title || 'Interactive Road Intervention',
      description: `Manual toggle of ${roadId}`,
      closed_road_ids: updatedClosed,
      shelter_capacity_multipliers: activeScenario?.shelter_capacity_multipliers || {},
      hazard_radius_multiplier: activeScenario?.hazard_radius_multiplier || 1.0,
      evacuation_speed_multiplier: activeScenario?.evacuation_speed_multiplier || 1.0,
      quarantine_lockdown_zone_ids: activeScenario?.quarantine_lockdown_zone_ids || []
    };

    applyWhatIf(updatedScenario);
  };

  const handleEvaluateScenario = async (scenario: WhatIfScenario) => {
    setIsEvaluating(true);
    setEvaluatingScenario(scenario);
    const result = await evaluateWhatIf(scenario);
    setIsEvaluating(false);
    if (result) {
      setComparisonResult(result);
      setIsCompareModalOpen(true);
    }
  };

  const handleApplyEvaluatedScenario = () => {
    if (evaluatingScenario) {
      applyWhatIf(evaluatingScenario);
    }
  };

  if (isLoading && !state) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-300">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
        <h2 className="text-lg font-bold text-white tracking-wide">CONNECTING TO TWINEVAC DIGITAL TWIN...</h2>
        <p className="text-xs text-slate-500 mt-1">Initializing Salem urban network, shelters, and AI models</p>
      </div>
    );
  }

  const currentPrediction = selectedHorizon !== 'now' ? state?.predictions[selectedHorizon] : undefined;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Operations Telemetry Header */}
      <TelemetryHeader
        state={state}
        isConnected={isConnected}
        onStart={startSimulation}
        onPause={pauseSimulation}
        onStep={stepSimulation}
        onReset={resetSimulation}
        onSetSpeed={setSpeed}
        onOpenReportModal={() => setIsReportModalOpen(true)}
      />

      {/* Main SaaS Operations Command Layout */}
      <main className="flex-1 p-5 max-w-[1720px] w-full mx-auto grid grid-cols-1 xl:grid-cols-12 gap-5">
        {/* Left & Center: Digital Twin Visual & Spatial Command (8 cols) */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          {/* Predictive Horizon Timeline Scrubber */}
          <PredictionHorizon
            selectedHorizon={selectedHorizon}
            onSelectHorizon={setSelectedHorizon}
            predictions={state?.predictions}
          />

          {/* Interactive 2.5D Digital Twin Canvas */}
          <MapView
            roads={state?.roads || []}
            shelters={state?.shelters || []}
            zones={state?.zones || []}
            agents={state?.agents || []}
            selectedHorizon={selectedHorizon}
            predictionData={currentPrediction}
            activeScenario={activeScenario}
            onToggleRoadClosure={handleToggleRoadClosure}
          />

          {/* AI Tactical Advisories & Anomaly Feed */}
          <AdvisoryFeed
            advisories={state?.advisories || []}
            anomalies={state?.anomalies || []}
          />
        </div>

        {/* Right: What-If Sandbox & Shelter Operations (4 cols) */}
        <div className="xl:col-span-4 flex flex-col gap-4">
          {/* What-If Counterfactual Sandbox Panel */}
          <WhatIfPanel
            roads={state?.roads || []}
            activeScenario={activeScenario}
            onEvaluateScenario={handleEvaluateScenario}
            onApplyScenario={applyWhatIf}
            onClearScenario={clearWhatIf}
            isEvaluating={isEvaluating}
          />

          {/* Shelter & Quarantine Bed Capacity Gauges */}
          <ShelterGauges shelters={state?.shelters || []} />
        </div>
      </main>

      {/* Comparative Scenario Delta Modal */}
      <ScenarioCompareModal
        isOpen={isCompareModalOpen}
        onClose={() => setIsCompareModalOpen(false)}
        result={comparisonResult}
        scenario={evaluatingScenario}
        onApplyLive={handleApplyEvaluatedScenario}
      />

      {/* Export Official Audit Report Modal */}
      <ExportReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        state={state}
      />
    </div>
  );
};

export default App;
