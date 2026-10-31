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
import { AIModelHubModal } from './components/AIModelHubModal';
import { WeatherControlModal } from './components/WeatherControlModal';
import { AnalyticsTrendsModal } from './components/AnalyticsTrendsModal';
import { WhatIfScenario, ScenarioComparisonResult } from './types/digital_twin';

export const App: React.FC = () => {
  const {
    state,
    isConnected,
    isLoading,
    error,
    clearError,
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
  const [isAIModalOpen, setIsAIModalOpen] = useState<boolean>(false);
  const [isWeatherModalOpen, setIsWeatherModalOpen] = useState<boolean>(false);
  const [isAnalyticsModalOpen, setIsAnalyticsModalOpen] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<ScenarioComparisonResult | null>(null);
  const [evaluatingScenario, setEvaluatingScenario] = useState<WhatIfScenario | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  // Road closure toggle handler
  const handleToggleRoadClosure = (rawRoadId: string) => {
    if (!state) return;
    // The backend closes/reopens both directions together, so always work with the forward id
    const roadId = rawRoadId.endsWith('_REV') ? rawRoadId.slice(0, -4) : rawRoadId;
    const isCurrentlyClosed = state.roads.find(r => r.id === roadId)?.is_closed;
    const currentClosed = (activeScenario?.closed_road_ids || []).map(id => (id.endsWith('_REV') ? id.slice(0, -4) : id));
    const updatedClosed = isCurrentlyClosed
      ? currentClosed.filter(id => id !== roadId)
      : Array.from(new Set([...currentClosed, roadId]));

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
    // on failure the hook has already raised a visible error banner
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
        {error && (
          <div className="mt-5 max-w-lg text-center text-xs text-rose-300 bg-rose-950/60 border border-rose-800 rounded-lg px-4 py-3">
            {error}
          </div>
        )}
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
        onOpenAIModal={() => setIsAIModalOpen(true)}
        onOpenWeatherModal={() => setIsWeatherModalOpen(true)}
        onOpenAnalyticsModal={() => setIsAnalyticsModalOpen(true)}
      />

      {/* Backend / request error banner */}
      {error && (
        <div className="bg-rose-950/80 border-b border-rose-800 text-rose-200 text-xs px-6 py-2 flex items-center justify-between gap-4">
          <span>{error}</span>
          <button onClick={clearError} className="font-bold text-rose-300 hover:text-white cursor-pointer">Dismiss</button>
        </div>
      )}

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

      {/* AI & ML Models Hub Modal */}
      <AIModelHubModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        mlStatus={state?.ml_service_status}
      />

      {/* Environmental & Weather Simulation Modal */}
      <WeatherControlModal
        isOpen={isWeatherModalOpen}
        onClose={() => setIsWeatherModalOpen(false)}
        currentWeather={state?.weather}
      />

      {/* Real-time Analytics & Trendlines Modal */}
      <AnalyticsTrendsModal
        isOpen={isAnalyticsModalOpen}
        onClose={() => setIsAnalyticsModalOpen(false)}
        state={state}
      />
    </div>
  );
};

export default App;
