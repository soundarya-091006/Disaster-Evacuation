/**
 * Backend location. Override at build/run time with:
 *   VITE_API_URL=http://192.168.1.20:8000 npm run dev
 *   VITE_WS_URL=ws://192.168.1.20:8000/ws/telemetry   (optional, derived from VITE_API_URL otherwise)
 */
export const API_BASE: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const API_BASE_URL = API_BASE;

export const WS_URL: string =
  import.meta.env.VITE_WS_URL ?? `${API_BASE.replace(/^http/, 'ws')}/ws/telemetry`;
