import React, { useState } from 'react';
import { Cpu, Brain, CheckCircle, RefreshCw, X, ShieldAlert, Activity, GitFork, BarChart3, Clock } from 'lucide-react';
import { MLServiceStatus } from '../types/digital_twin';
import { API_BASE_URL } from '../config';

interface AIModelHubModalProps {
  isOpen: boolean;
  onClose: () => void;
  mlStatus?: MLServiceStatus;
  onRetrainComplete?: () => void;
}

export const AIModelHubModal: React.FC<AIModelHubModalProps> = ({
  isOpen,
  onClose,
  mlStatus,
  onRetrainComplete
}) => {
  const [isRetraining, setIsRetraining] = useState<boolean>(false);
  const [retrainMessage, setRetrainMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRetrain = async () => {
    setIsRetraining(true);
    setRetrainMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ml/retrain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ epochs: 25, synthetic_samples: 1800 })
      });
      if (!res.ok) throw new Error('Retraining request failed');
      const data = await res.json();
      setRetrainMessage('All AI/ML models successfully retrained and hot-reloaded into memory!');
      if (onRetrainComplete) onRetrainComplete();
    } catch (err: any) {
      setRetrainMessage(`Retraining failed: ${err.message}`);
    } finally {
      setIsRetraining(false);
    }
  };

  const featureImportances = mlStatus?.models_active?.risk_classifier?.feature_importances || {
    flood_depth_cm: 0.4922,
    contagion_score: 0.2110,
    is_closed: 0.1317,
    congestion_index: 0.0867,
    current_speed_kmh: 0.0519,
    rainfall_mmh: 0.0208,
    capacity_pcu: 0.0057
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl shadow-cyan-950/40">
        
        {/* Header */}
        <div className="px-6 py-4 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-cyan-400">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Enterprise AI & Machine Learning Hub</h2>
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-[10px] font-mono font-bold flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />
                  {mlStatus?.status || 'OPERATIONAL'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                PyTorch LSTM Neural Forecaster • Scikit-Learn Random Forest Classifier • Isolation Forest Surge Engine • Q-Learning Graph Policy
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200">
          
          {/* Top KPI Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Inference Latency</span>
              <span className="text-xl font-bold font-mono text-cyan-400 mt-1 block">
                {mlStatus?.last_inference_latency_ms || 0.85} <span className="text-xs text-slate-500">ms</span>
              </span>
              <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-0.5">
                <Activity className="w-2.5 h-2.5" /> Vector Batched
              </span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Risk Classifier Acc</span>
              <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">
                {mlStatus?.models_active?.risk_classifier?.accuracy_pct || 91.92}%
              </span>
              <span className="text-[10px] text-slate-400">F1: {mlStatus?.models_active?.risk_classifier?.f1_score || 0.9187}</span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Traffic LSTM R² Score</span>
              <span className="text-xl font-bold font-mono text-amber-400 mt-1 block">
                {mlStatus?.models_active?.traffic_lstm?.r2_score || 0.9468}
              </span>
              <span className="text-[10px] text-slate-400">15m / 30m / 60m horizons</span>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Q-Learning Policy</span>
              <span className="text-xl font-bold font-mono text-purple-400 mt-1 block">
                {mlStatus?.models_active?.q_routing_agent?.states_learned || 64} <span className="text-xs text-slate-500">states</span>
              </span>
              <span className="text-[10px] text-purple-300">SARSA / TD-0 Graph Agent</span>
            </div>
          </div>

          {/* Active Model Architectures */}
          <div>
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Trained Model Architectures & Runtime Pipelines
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              
              {/* Traffic LSTM */}
              <div className="bg-slate-950/50 border border-slate-800/80 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-cyan-300 flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-cyan-400" /> PyTorch Traffic LSTM
                    </h4>
                    <span className="px-2 py-0.5 bg-cyan-950 text-cyan-400 border border-cyan-800 rounded text-[10px] font-mono">
                      Deep Learning
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Sequence recurrent model predicting dynamic BPR congestion index and road travel speeds across 15m, 30m, and 60m time horizons with uncertainty bands.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Params: ~37,126</span>
                  <span>Device: CPU Vectorized</span>
                </div>
              </div>

              {/* Random Forest Classifier */}
              <div className="bg-slate-950/50 border border-slate-800/80 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-emerald-300 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-emerald-400" /> Multi-Hazard Risk Classifier
                    </h4>
                    <span className="px-2 py-0.5 bg-emerald-950 text-emerald-400 border border-emerald-800 rounded text-[10px] font-mono">
                      Random Forest
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Ensemble of 100 decision trees synthesizing flood water depth, airborne contagion corridor exposure, and capacity volume into categorical risk tiers.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Accuracy: 91.92%</span>
                  <span>Classes: 4 Tiers</span>
                </div>
              </div>

              {/* Isolation Forest */}
              <div className="bg-slate-950/50 border border-slate-800/80 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-rose-300 flex items-center gap-1.5">
                      <Activity className="w-4 h-4 text-rose-400" /> Isolation Forest Surge Engine
                    </h4>
                    <span className="px-2 py-0.5 bg-rose-950 text-rose-400 border border-rose-800 rounded text-[10px] font-mono">
                      Unsupervised
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Isolates statistical outliers in travel speed drops and 240%+ volume surge spikes to trigger automated EOC tactical warnings.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Contamination: 6.0%</span>
                  <span>Latency: &lt;1.0 ms</span>
                </div>
              </div>

              {/* Q-Routing Agent */}
              <div className="bg-slate-950/50 border border-slate-800/80 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-purple-300 flex items-center gap-1.5">
                      <GitFork className="w-4 h-4 text-purple-400" /> Reinforcement Learning Router
                    </h4>
                    <span className="px-2 py-0.5 bg-purple-950 text-purple-400 border border-purple-800 rounded text-[10px] font-mono">
                      Q-Learning
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    Learns state-action Q-values balancing travel time against shelter saturation penalties to achieve global traffic equilibrium.
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
                  <span>Episodes: 2,500</span>
                  <span>States: 64 Pairs</span>
                </div>
              </div>

            </div>
          </div>

          {/* Feature Importance Distribution */}
          <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              Multi-Hazard Random Forest Feature Attribution
            </h3>
            <div className="space-y-2">
              {Object.entries(featureImportances).map(([feat, val]: [string, any]) => {
                const pct = Math.round(Number(val) * 100);
                return (
                  <div key={feat} className="text-xs">
                    <div className="flex justify-between text-slate-300 mb-1">
                      <span className="font-mono">{feat}</span>
                      <span className="font-mono text-cyan-400 font-bold">{pct}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-cyan-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(4, pct)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Retrain Feedback */}
          {retrainMessage && (
            <div className={`p-3 rounded-xl text-xs font-medium border ${
              retrainMessage.includes('failed')
                ? 'bg-rose-950/60 border-rose-800 text-rose-300'
                : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            }`}>
              {retrainMessage}
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-950/70 border-t border-slate-800 flex items-center justify-between">
          <div className="text-[11px] text-slate-500">
            Last retrained: {mlStatus?.last_trained_timestamp || 'Active Session'}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRetrain}
              disabled={isRetraining}
              className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-cyan-900/30 flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRetraining ? 'animate-spin' : ''}`} />
              {isRetraining ? 'Retraining Models...' : 'Retrain & Fine-tune Models'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
