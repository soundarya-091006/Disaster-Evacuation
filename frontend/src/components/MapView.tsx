import React, { useRef, useEffect, useState, useCallback } from 'react';
import { 
  RoadSegment, RoadNode, ShelterHospital, EvacuationZone, 
  EvacuationAgent, PredictionHorizonData, WhatIfScenario 
} from '../types/digital_twin';
import { 
  ZoomIn, ZoomOut, Maximize2, Shield, Eye, 
  Layers, MapPin, AlertCircle, Ban, CheckCircle2 
} from 'lucide-react';

interface MapViewProps {
  roads: RoadSegment[];
  shelters: ShelterHospital[];
  zones: EvacuationZone[];
  agents: EvacuationAgent[];
  selectedHorizon: 'now' | '15m' | '30m' | '60m';
  predictionData?: PredictionHorizonData;
  activeScenario: WhatIfScenario | null;
  onToggleRoadClosure: (roadId: string) => void;
}

// Bounding box for Salem metropolitan area
const SALEM_BOUNDS = {
  minLat: 11.6150,
  maxLat: 11.7050,
  minLng: 78.0650,
  maxLng: 78.2350
};

export const MapView: React.FC<MapViewProps> = ({
  roads,
  shelters,
  zones,
  agents,
  selectedHorizon,
  predictionData,
  activeScenario,
  onToggleRoadClosure
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Transform state for pan and zoom
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Layer toggles
  const [showAgents, setShowAgents] = useState<boolean>(true);
  const [showHazards, setShowHazards] = useState<boolean>(true);
  const [showShelters, setShowShelters] = useState<boolean>(true);
  const [selectedRoad, setSelectedRoad] = useState<RoadSegment | null>(null);

  // Geographic projection helper: (lat, lng) -> Canvas (x, y)
  const project = useCallback((lat: number, lng: number, width: number, height: number) => {
    const latSpan = SALEM_BOUNDS.maxLat - SALEM_BOUNDS.minLat;
    const lngSpan = SALEM_BOUNDS.maxLng - SALEM_BOUNDS.minLng;

    // Invert Y because canvas Y increases downwards, whereas latitude increases upwards
    const x = ((lng - SALEM_BOUNDS.minLng) / lngSpan) * width;
    const y = ((SALEM_BOUNDS.maxLat - lat) / latSpan) * height;

    return {
      x: x * zoom + pan.x,
      y: y * zoom + pan.y
    };
  }, [zoom, pan]);

  // Main Canvas Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high DPI displays
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // 1. Draw subtle tactical grid
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 0.5;
    const gridSize = 40 * zoom;
    const offsetX = pan.x % gridSize;
    const offsetY = pan.y % gridSize;

    ctx.beginPath();
    for (let x = offsetX; x < width; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
    }
    for (let y = offsetY; y < height; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
    }
    ctx.stroke();

    // 2. Draw Hazard & Epidemic Contagion Zones
    if (showHazards) {
      zones.forEach((zone) => {
        const centerPt = project(zone.center.lat, zone.center.lng, width, height);
        const radius = (zone.risk_score * 55 + 25) * zoom;

        // Gradient circle
        const grad = ctx.createRadialGradient(centerPt.x, centerPt.y, 5, centerPt.x, centerPt.y, radius);
        if (zone.hazard_type.includes('flood')) {
          grad.addColorStop(0, 'rgba(56, 189, 248, 0.45)');
          grad.addColorStop(0.7, 'rgba(14, 116, 144, 0.25)');
          grad.addColorStop(1, 'rgba(8, 51, 68, 0.0)');
        } else {
          grad.addColorStop(0, 'rgba(239, 68, 68, 0.45)');
          grad.addColorStop(0.7, 'rgba(185, 28, 28, 0.25)');
          grad.addColorStop(1, 'rgba(127, 29, 29, 0.0)');
        }

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(centerPt.x, centerPt.y, radius, 0, Math.PI * 2);
        ctx.fill();

        // Pulsing boundary stroke
        ctx.strokeStyle = zone.hazard_type.includes('flood') ? 'rgba(56, 189, 248, 0.6)' : 'rgba(239, 68, 68, 0.6)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.arc(centerPt.x, centerPt.y, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Zone label
        ctx.fillStyle = '#cbd5e1';
        ctx.font = `bold ${Math.max(9, 10 * zoom)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(zone.name, centerPt.x, centerPt.y - radius - 4);
      });
    }

    // Node coordinate lookup mapping
    const nodeCoords: Record<string, { lat: number; lng: number }> = {
      NODE_SALEM_JN: { lat: 11.6702, lng: 78.1189 },
      NODE_SURAMANGALAM: { lat: 11.6730, lng: 78.1235 },
      NODE_MEYYANUR: { lat: 11.6650, lng: 78.1350 },
      NODE_FOUR_ROADS: { lat: 11.6608, lng: 78.1442 },
      NODE_COLLECTORATE: { lat: 11.6670, lng: 78.1520 },
      NODE_HASTHAMPATTI: { lat: 11.6765, lng: 78.1565 },
      NODE_ALAGAPURAM: { lat: 11.6820, lng: 78.1330 },
      NODE_GORIMEDU: { lat: 11.6980, lng: 78.1720 },
      NODE_GMKMC_HOSP: { lat: 11.6580, lng: 78.1590 },
      NODE_AMMAPET: { lat: 11.6540, lng: 78.1812 },
      NODE_AYODHIYAPATTINAM: { lat: 11.6520, lng: 78.2300 },
      NODE_SHEVAPET: { lat: 11.6492, lng: 78.1360 },
      NODE_GUGAI: { lat: 11.6405, lng: 78.1495 },
      NODE_ANNADHANAPATTI: { lat: 11.6360, lng: 78.1410 },
      NODE_KONDALAMPATTI: { lat: 11.6210, lng: 78.1250 },
      NODE_SEELANAIKENPATTI: { lat: 11.6235, lng: 78.1630 },
      NODE_STEEL_PLANT: { lat: 11.6680, lng: 78.0720 }
    };

    // 3. Draw Road Network
    roads.forEach((road) => {
      const src = nodeCoords[road.source];
      const tgt = nodeCoords[road.target];
      if (!src || !tgt) return;

      const p1 = project(src.lat, src.lng, width, height);
      const p2 = project(tgt.lat, tgt.lng, width, height);

      // Determine road color
      let strokeColor = '#10b981'; // free flow green
      let lineWidth = Math.max(2, (road.lanes * 1.5) * zoom);

      const isForecastHorizon = selectedHorizon !== 'now' && predictionData;
      const isPredictedBottleneck = isForecastHorizon && predictionData?.high_risk_road_ids.includes(road.id);

      if (road.is_closed) {
        strokeColor = '#475569'; // closed gray
        ctx.setLineDash([5, 5]);
      } else if (isPredictedBottleneck || road.risk_level === 'CRITICAL' || road.congestion_index > 0.85) {
        strokeColor = '#ef4444'; // critical red
        lineWidth += 2;
        ctx.setLineDash([]);
      } else if (road.risk_level === 'HIGH' || road.congestion_index > 0.65) {
        strokeColor = '#f59e0b'; // amber
        ctx.setLineDash([]);
      } else if (road.risk_level === 'MEDIUM' || road.congestion_index > 0.40) {
        strokeColor = '#3b82f6'; // moderate blue
        ctx.setLineDash([]);
      } else {
        ctx.setLineDash([]);
      }

      // Check if selected
      if (selectedRoad?.id === road.id) {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = lineWidth + 3;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }

      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw closure 'X' marker if road is closed
      if (road.is_closed) {
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;
        ctx.fillStyle = '#ef4444';
        ctx.beginPath();
        ctx.arc(midX, midY, 6 * zoom, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${10 * zoom}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('✕', midX, midY);
      }
    });

    // 4. Draw Intersections & Nodes
    Object.entries(nodeCoords).forEach(([nodeId, coord]) => {
      const pt = project(coord.lat, coord.lng, width, height);
      ctx.fillStyle = '#334155';
      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, Math.max(3, 4 * zoom), 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

    // 5. Draw Evacuee Agents / Convoys in transit
    if (showAgents) {
      agents.forEach((agent) => {
        if (agent.status !== 'in_transit') return;

        const pt = project(agent.current_lat, agent.current_lng, width, height);

        let color = '#38bdf8'; // standard convoy cyan
        let radius = Math.max(3, 4.5 * zoom);

        if (agent.agent_type === 'ambulance') {
          color = '#f43f5e'; // rose/red for medical
          radius = Math.max(4, 6 * zoom);
        } else if (agent.agent_type === 'emergency_bus') {
          color = '#eab308'; // yellow for buses
          radius = Math.max(4, 5.5 * zoom);
        }

        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0; // reset shadow
      });
    }

    // 6. Draw Safe Shelters & Hospitals
    if (showShelters) {
      shelters.forEach((shelter) => {
        const pt = project(shelter.lat, shelter.lng, width, height);
        const radius = Math.max(14, 16 * zoom);

        // Facility Base circle
        ctx.fillStyle = shelter.type === 'hospital_quarantine' ? '#0f766e' : '#1e3a8a';
        ctx.strokeStyle = shelter.status === 'FULL' ? '#ef4444' : (shelter.status === 'NEAR_CAPACITY' ? '#f59e0b' : '#38bdf8');
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Facility Label & Occupancy Gauge
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.max(9, 10 * zoom)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(shelter.type === 'hospital_quarantine' ? 'H' : 'S', pt.x, pt.y);

        // Name tag & percentage
        ctx.font = `bold ${Math.max(8, 9 * zoom)}px sans-serif`;
        ctx.fillStyle = '#e2e8f0';
        ctx.textBaseline = 'bottom';
        const occPct = shelter.occupancy_pct ?? Math.round((shelter.occupied / Math.max(shelter.total_capacity, 1)) * 100);
        ctx.fillText(`${shelter.name.split(' ')[0]} (${occPct.toFixed(0)}%)`, pt.x, pt.y - radius - 2);
      });
    }

  }, [roads, shelters, zones, agents, zoom, pan, showAgents, showHazards, showShelters, selectedRoad, selectedHorizon, predictionData, project]);

  // Handle Canvas Resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current && canvasRef.current) {
        canvasRef.current.width = containerRef.current.clientWidth;
        canvasRef.current.height = containerRef.current.clientHeight;
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Zoom helpers
  const handleZoomIn = () => setZoom((z) => Math.min(3.5, z * 1.25));
  const handleZoomOut = () => setZoom((z) => Math.max(0.6, z / 1.25));
  const handleResetView = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
    setSelectedRoad(null);
  };

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-[580px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl select-none"
    >
      {/* 2.5D Digital Twin Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="w-full h-full cursor-grab active:cursor-grabbing block"
      />

      {/* Floating Map Legend & Status Bar */}
      <div className="absolute top-4 left-4 bg-slate-900/90 border border-slate-800 rounded-xl px-3.5 py-2.5 backdrop-blur-md shadow-lg pointer-events-auto">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          <span>Salem Live Twin Map</span>
          {activeScenario && (
            <span className="bg-amber-950 border border-amber-800 text-amber-300 text-[10px] px-1.5 py-0.2 rounded font-mono ml-1">
              SCENARIO ACTIVE
            </span>
          )}
        </div>

        {/* Legend color codes */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px] text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>Flowing (&lt;40% V/C)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>Moderate (40-75%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
            <span>Bottleneck (&gt;75%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-pulse" />
            <span>Contagion Hazard</span>
          </div>
        </div>
      </div>

      {/* Floating Layer Controls & Map Tools */}
      <div className="absolute top-4 right-4 flex flex-col gap-2 pointer-events-auto">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-1 backdrop-blur-md shadow-lg flex flex-col gap-1">
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-slate-800 text-slate-300 rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-slate-800 text-slate-300 rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetView}
            className="p-2 hover:bg-slate-800 text-slate-300 rounded-lg transition-colors"
            title="Reset Pan/Zoom"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>

        {/* Visibility Toggles */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-1.5 backdrop-blur-md shadow-lg flex flex-col gap-1.5 text-xs">
          <button
            onClick={() => setShowAgents(!showAgents)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${
              showAgents ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="w-3.5 h-3.5" /> Convoys
          </button>
          <button
            onClick={() => setShowHazards(!showHazards)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-colors ${
              showHazards ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-3.5 h-3.5" /> Hazards
          </button>
        </div>
      </div>

      {/* Road Segment Inspection Card (Bottom Right) */}
      <div className="absolute bottom-4 left-4 bg-slate-900/95 border border-slate-800 rounded-xl p-3 backdrop-blur-md shadow-xl max-w-sm pointer-events-auto">
        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
          <span>Active Arterials Monitor</span>
          <span className="text-cyan-400">{roads.filter(r => !r.is_closed).length} open corridors</span>
        </div>
        <div className="max-h-24 overflow-y-auto space-y-1 pr-1">
          {roads.slice(0, 4).map((r) => (
            <div 
              key={r.id}
              onClick={() => onToggleRoadClosure(r.id)}
              className="flex items-center justify-between text-xs p-1.5 rounded-lg bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition-all"
            >
              <div className="truncate mr-2">
                <div className="font-semibold text-slate-200 truncate">{r.name}</div>
                <div className="text-[10px] text-slate-400">{r.current_speed_kmh} km/h • {r.risk_level} Risk</div>
              </div>
              <button 
                className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase transition-colors shrink-0 ${
                  r.is_closed 
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-red-950 text-red-400 border border-red-800 hover:bg-red-900'
                }`}
              >
                {r.is_closed ? 'Reopen' : 'Sim Block'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
