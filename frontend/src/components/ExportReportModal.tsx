import React, { useState } from 'react';
import { SimulationStepState } from '../types/digital_twin';
import { X, FileText, Download, Check, ShieldCheck, Database } from 'lucide-react';
import { API_BASE as REST_BASE } from '../config';

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  state: SimulationStepState | null;
}


export const ExportReportModal: React.FC<ExportReportModalProps> = ({
  isOpen,
  onClose,
  state
}) => {
  const [downloadingPdf, setDownloadingPdf] = useState<boolean>(false);
  const [downloadingJson, setDownloadingJson] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Shared download helper with error feedback and object-URL cleanup
  const download = async (path: string, filename: string) => {
    setError(null);
    const res = await fetch(`${REST_BASE}${path}`);
    if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  };

  if (!isOpen || !state) return null;

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true);
      await download('/reports/export-pdf', `TwinEvac_Audit_Report_${Date.now()}.pdf`);
    } catch (err) {
      console.error("PDF download failed:", err);
      setError('PDF export failed. Check that the backend is running.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadJson = async () => {
    try {
      setDownloadingJson(true);
      await download('/reports/export-json', `TwinEvac_Snapshot_${Date.now()}.json`);
    } catch (err) {
      console.error("JSON download failed:", err);
      setError('JSON export failed. Check that the backend is running.');
    } finally {
      setDownloadingJson(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-slate-950 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-950 border border-cyan-800 text-cyan-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white m-0">Generate Incident Audit Report</h2>
              <p className="text-xs text-slate-400 m-0">Official Evacuation Audit Documentation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Jurisdiction:</span>
              <span className="font-semibold text-slate-200">Salem District Disaster Management Authority</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Simulation Timestamp:</span>
              <span className="font-mono text-cyan-400">T+{state.elapsed_sim_minutes} minutes</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Total Evacuees Cleared:</span>
              <span className="font-bold text-emerald-400">{state.total_evacuated.toLocaleString()} ({state.evacuation_progress_pct}%)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Estimated Evacuation Time:</span>
              <span className="font-bold text-cyan-400">{state.estimated_evacuation_time_minutes} min</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Active Scenario:</span>
              <span className="font-bold text-indigo-400">{state.active_scenario?.title ?? 'Baseline Operations'}</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed m-0">
            Exported documents contain complete time-series telemetry, predictive 15m/30m/60m congestion tables, shelter fill logs, and timestamped AI routing advisories compliant with standard incident audit protocols.
          </p>

          {error && (
            <div className="text-xs text-rose-300 bg-rose-950/60 border border-rose-800 rounded-lg px-3 py-2">{error}</div>
          )}

          {/* Download Buttons */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <button
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="flex items-center justify-center gap-2 p-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold rounded-xl shadow-lg transition-all"
            >
              <Download className="w-4 h-4" />
              {downloadingPdf ? 'Compiling PDF...' : 'Download PDF Audit'}
            </button>

            <button
              onClick={handleDownloadJson}
              disabled={downloadingJson}
              className="flex items-center justify-center gap-2 p-3 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 transition-all"
            >
              <Database className="w-4 h-4" />
              {downloadingJson ? 'Exporting JSON...' : 'Export Raw JSON'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
