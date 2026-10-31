import { useState, useEffect, useRef, useCallback } from 'react';
import { SimulationStepState, WhatIfScenario, ScenarioComparisonResult } from '../types/digital_twin';

import { API_BASE as REST_BASE, WS_URL } from '../config';

const OFFLINE_MSG = 'Cannot reach the TwinEvac backend. Start it with: cd backend && python -m uvicorn app.main:app --port 8000';

export function useDigitalTwinSocket() {
  const [state, setState] = useState<SimulationStepState | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedHorizon, setSelectedHorizon] = useState<'now' | '15m' | '30m' | '60m'>('now');
  const [activeScenario, setActiveScenario] = useState<WhatIfScenario | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  // Initial fetch fallback
  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${REST_BASE}/twin/state`);
      if (res.ok) {
        const data = await res.json();
        setState(data);
        setActiveScenario(data.active_scenario ?? null);
        setIsLoading(false);
        setError(null);
      }
    } catch (err) {
      console.warn("REST fetch fallback error:", err);
      setError(OFFLINE_MSG);
    }
  }, []);

  // POST helper: surfaces failures to the UI instead of silently ignoring them
  const post = useCallback(async (path: string, body?: unknown): Promise<Response | null> => {
    try {
      const res = await fetch(`${REST_BASE}${path}`, {
        method: 'POST',
        headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
        body: body !== undefined ? JSON.stringify(body) : undefined
      });
      if (!res.ok) {
        setError(`Request ${path} failed (HTTP ${res.status}).`);
        return null;
      }
      setError(null);
      return res;
    } catch (e) {
      console.error(`POST ${path} failed:`, e);
      setError(OFFLINE_MSG);
      return null;
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
        setError(null);
        console.log("TwinEvac WebSocket Connected.");
      };

      ws.onmessage = (event) => {
        try {
          const incoming: SimulationStepState = JSON.parse(event.data);
          setState(incoming);
          // Mirror the server: also clears the badge when another operator clears the scenario
          setActiveScenario(incoming.active_scenario ?? null);
          setIsLoading(false);
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

    // Secondary REST fallback only when the WebSocket is not open.
    const interval = setInterval(() => {
      if (
        !socketRef.current ||
        socketRef.current.readyState !== WebSocket.OPEN
      ) {
        fetchState();
      }
    }, 4000);

    return () => {
      clearInterval(interval);

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [fetchState, connectWebSocket]);
  // Simulation Controls
  const startSimulation = async () => {
    if (await post('/sim/start')) await fetchState();
  };

  const pauseSimulation = async () => {
    if (await post('/sim/pause')) await fetchState();
  };

  const stepSimulation = async () => {
    const res = await post('/sim/step');
    if (res) setState(await res.json());
  };

  const resetSimulation = async () => {
    const res = await post('/sim/reset');
    if (res) {
      setState(await res.json());
      setActiveScenario(null);
    }
  };

  const setSpeed = async (multiplier: number) => {
    if (await post('/sim/speed', { multiplier })) await fetchState();
  };

  // What-If Evaluation & Application
  const evaluateWhatIf = async (scenario: WhatIfScenario): Promise<ScenarioComparisonResult | null> => {
    const res = await post('/analytics/what-if/evaluate', scenario);
    return res ? await res.json() : null;
  };

  const applyWhatIf = async (scenario: WhatIfScenario) => {
    const res = await post('/analytics/what-if/apply', scenario);
    if (res) {
      setState(await res.json());
      setActiveScenario(scenario);
    }
  };

  const clearWhatIf = async () => {
    const res = await post('/analytics/what-if/clear');
    if (res) {
      setState(await res.json());
      setActiveScenario(null);
    }
  };

  return {
    state,
    isConnected,
    isLoading,
    error,
    clearError: () => setError(null),
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
