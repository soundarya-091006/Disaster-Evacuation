import React, { useState } from 'react';
import { CloudRain, CloudLightning, Sun, Wind, Droplets, X, Check, Waves } from 'lucide-react';
import { WeatherState } from '../types/digital_twin';
import { API_BASE_URL } from '../config';

interface WeatherControlModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentWeather?: WeatherState;
  onWeatherUpdated?: () => void;
}

export const WeatherControlModal: React.FC<WeatherControlModalProps> = ({
  isOpen,
  onClose,
  currentWeather,
  onWeatherUpdated
}) => {
  const [rainfall, setRainfall] = useState<number>(currentWeather?.rainfall_intensity_mmh || 35);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  if (!isOpen) return null;

  const presets = [
    { label: 'Clear Skies', rain: 0, icon: Sun, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
    { label: 'Moderate Monsoon', rain: 25, icon: CloudRain, color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
    { label: 'Torrential Downpour', rain: 60, icon: CloudLightning, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10' },
    { label: 'Extreme Inundation', rain: 95, icon: Waves, color: 'text-rose-400 border-rose-500/30 bg-rose-500/10' },
  ];

  const handleApply = async () => {
    setIsUpdating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/environment/weather`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rainfall_intensity_mmh: rainfall })
      });
      if (!res.ok) throw new Error('Weather update failed');
      if (onWeatherUpdated) onWeatherUpdated();
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdating(false);
    }
  };

  const floodMultiplier = Math.max(0.2, (rainfall / 30.0)).toFixed(2);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-lg w-full overflow-hidden flex flex-col shadow-2xl shadow-blue-950/40">
        
        {/* Header */}
        <div className="px-6 py-4 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-xl text-blue-400">
              <CloudRain className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">Environmental & Weather Simulator</h2>
              <p className="text-xs text-slate-400">Modulate real-time precipitation, runoff waterlogging & flood depth</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 text-slate-200">
          
          {/* Quick Presets */}
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Disaster Meteorological Presets
            </label>
            <div className="grid grid-cols-2 gap-2">
              {presets.map((p) => {
                const Icon = p.icon;
                const isSelected = Math.abs(rainfall - p.rain) < 5;
                return (
                  <button
                    key={p.label}
                    onClick={() => setRainfall(p.rain)}
                    className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all cursor-pointer ${
                      isSelected
                        ? `${p.color} ring-2 ring-blue-500/50`
                        : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <div>
                      <div className="text-xs font-bold leading-tight">{p.label}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{p.rain} mm/h</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Interactive Rainfall Slider */}
          <div className="bg-slate-950/50 border border-slate-800 p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
                <Droplets className="w-4 h-4 text-cyan-400" />
                Rainfall Intensity (Precipitation)
              </span>
              <span className="text-base font-bold font-mono text-cyan-400">
                {rainfall} <span className="text-xs text-slate-500">mm/h</span>
              </span>
            </div>

            <input
              type="range"
              min="0"
              max="120"
              step="5"
              value={rainfall}
              onChange={(e) => setRainfall(Number(e.target.value))}
              className="w-full accent-cyan-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />

            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0 (Dry)</span>
              <span>40 (Monsoon)</span>
              <span>80 (Cloudburst)</span>
              <span>120 (Extreme)</span>
            </div>
          </div>

          {/* Impact preview */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Flood Surge Factor</span>
              <span className="text-base font-bold font-mono text-blue-400 mt-1 block">
                {floodMultiplier}x
              </span>
            </div>
            <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Vulnerable Corridors</span>
              <span className="text-base font-bold font-mono text-amber-400 mt-1 block">
                {rainfall > 40 ? '6 Inundated' : rainfall > 15 ? '3 Waterlogged' : '0 Free-flow'}
              </span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-950/70 border-t border-slate-800 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={isUpdating}
            className="px-5 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-900/30 flex items-center gap-2 cursor-pointer"
          >
            <Check className="w-4 h-4" />
            {isUpdating ? 'Applying...' : 'Apply Meteorological State'}
          </button>
        </div>

      </div>
    </div>
  );
};
