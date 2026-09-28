import { useState, useEffect, useRef, useCallback } from 'react';
import { SimulationStepState, WhatIfScenario, ScenarioComparisonResult } from '../types/digital_twin';

const WS_URL = window.location.protocol === 'https:'
  ? `wss://${window.location.host}/ws/telemetry`
  : `ws://${window.location.hostname}:8000/ws/telemetry`;

const REST_BASE = window.location.port === '5173' ? 'http://localhost:8000' : '';

export function useDigitalTwinSocket() {
  const [state, setState] = useState<SimulationStepState | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedHorizon, setSelectedHorizon] = useState<'now' | '15m' | '30m' | '60m'>('now');
  const [activeScenario, setActiveScenario] = useState<WhatIfScenario | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  // Initial fetch fallback
  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${REST_BASE}/twin/state`);
      if (res.ok) {
        const data = await res.json();
        setState(data);
        setIsLoading(false);
      }
    } catch (err) {
      console.warn("REST fetch fallback error:", err);
    }
  }, []);

  // Connect WebSocket
  const connectWebSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    try {
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsLoading(false);
        console.log("TwinEvac WebSocket Connected.");
      };

      ws.onmessage = (event) => {
        try {
          const incoming: SimulationStepState = JSON.parse(event.data);
          setState(incoming);
          if (incoming.active_scenario) {
            setActiveScenario(incoming.active_scenario);
          }
        } catch (err) {
          console.error("Error parsing telemetry message:", err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnection after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };

      ws.onerror = (err) => {
        console.warn("WebSocket error, falling back to REST:", err);
        ws.close();
      };
    } catch (e) {
      console.warn("WebSocket initialization failed:", e);
    }
  }, []);

  useEffect(() => {
    fetchState();
    connectWebSocket();

    // Secondary poll every 4s if disconnected
    const interval = setInterval(() => {
      if (!isConnected) {
        fetchState();
      }
    }, 4000);

    return () => {
      clearInterval(interval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [fetchState, connectWebSocket, isConnected]);

  // Simulation Controls
  const startSimulation = async () => {
    await fetch(`${REST_BASE}/sim/start`, { method: 'POST' });
  };

  const pauseSimulation = async () => {
    await fetch(`${REST_BASE}/sim/pause`, { method: 'POST' });
  };

  const stepSimulation = async () => {
    const res = await fetch(`${REST_BASE}/sim/step`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      setState(data);
    }
  };

  const resetSimulation = async () => {
    const res = await fetch(`${REST_BASE}/sim/reset`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      setState(data);
      setActiveScenario(null);
    }
  };

  const setSpeed = async (multiplier: number) => {
    await fetch(`${REST_BASE}/sim/speed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ multiplier })
    });
  };

  // What-If Evaluation & Application
  const evaluateWhatIf = async (scenario: WhatIfScenario): Promise<ScenarioComparisonResult | null> => {
    try {
      const res = await fetch(`${REST_BASE}/analytics/what-if/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario)
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.error("Error evaluating scenario:", e);
    }
    return null;
  };

  const applyWhatIf = async (scenario: WhatIfScenario) => {
    try {
      const res = await fetch(`${REST_BASE}/analytics/what-if/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenario)
      });
      if (res.ok) {
        const data = await res.json();
        setState(data);
        setActiveScenario(scenario);
      }
    } catch (e) {
      console.error("Error applying scenario:", e);
    }
  };

  const clearWhatIf = async () => {
    try {
      const res = await fetch(`${REST_BASE}/analytics/what-if/clear`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setState(data);
        setActiveScenario(null);
      }
    } catch (e) {
      console.error("Error clearing scenario:", e);
    }
  };

  return {
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
  };
}
