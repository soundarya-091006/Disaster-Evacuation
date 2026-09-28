/**
 * TwinEvac - Digital Twin TypeScript Definitions
 */

export interface Coordinate {
  lat: float;
  lng: float;
}

export type float = number;

export interface RoadNode {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: string;
}

export interface RoadSegment {
  id: string;
  source: string;
  target: string;
  name: string;
  distance_km: number;
  lanes: number;
  free_flow_speed_kmh: number;
  capacity_pcu_per_hour: number;
  current_volume: number;
  current_speed_kmh: number;
  congestion_index: number; // 0.0 to 1.0
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  flood_depth_cm: number;
  contagion_exposure_score: number;
  is_closed: boolean;
  is_one_way: boolean;
  bottleneck_severity: number;
}

export interface ShelterHospital {
  id: string;
  name: string;
  type: 'hospital_quarantine' | 'relief_shelter' | 'community_safe_zone';
  lat: number;
  lng: number;
  total_capacity: number;
  occupied: number;
  quarantine_beds_total: number;
  quarantine_beds_occupied: number;
  intake_rate_per_min: number;
  status: 'OPEN' | 'NEAR_CAPACITY' | 'FULL' | 'ISOLATED';
  assigned_zone_ids: string[];
  occupancy_pct: number;
  quarantine_occupancy_pct?: number;
}

export interface EvacuationZone {
  id: string;
  name: string;
  center: Coordinate;
  boundary_coords: Coordinate[];
  total_population: number;
  evacuated_population: number;
  active_infections: number;
  hazard_type: string;
  risk_score: number;
  clearance_percentage: number;
}

export interface EvacuationAgent {
  id: string;
  origin_zone_id: string;
  destination_shelter_id: string;
  agent_type: 'pedestrian_group' | 'private_vehicle' | 'emergency_bus' | 'ambulance';
  size: number;
  current_edge_id: string;
  progress_on_edge: number;
  current_lat: number;
  current_lng: number;
  route: string[];
  route_edge_ids: string[];
  status: 'waiting' | 'in_transit' | 'arrived' | 'detoured';
  infection_exposure_accumulated: number;
}

export interface PredictionHorizonData {
  horizon_minutes: number;
  predicted_congested_road_count: number;
  predicted_average_speed_kmh: number;
  predicted_network_congestion_pct: number;
  high_risk_road_ids: string[];
  shelter_predicted_occupancy: Record<string, number>;
  predicted_bottlenecks: Array<{
    edge_id: string;
    road_name: string;
    source: string;
    target: string;
    predicted_congestion_index: number;
    confidence_range: [number, number];
    estimated_delay_min: number;
  }>;
  confidence_pct: number;
}

export interface WhatIfScenario {
  scenario_id: string;
  title: string;
  description: string;
  closed_road_ids: string[];
  shelter_capacity_multipliers: Record<string, number>;
  hazard_radius_multiplier: number;
  evacuation_speed_multiplier: number;
  quarantine_lockdown_zone_ids: string[];
}

export interface TacticalAdvisory {
  id: string;
  timestamp_sim_min: number;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  category: 'ROUTING' | 'QUARANTINE' | 'SHELTER_CAPACITY' | 'BOTTLENECK';
  title: string;
  message: string;
  recommended_action: string;
  affected_elements: string[];
  is_applied: boolean;
}

export interface AnomalyReport {
  id: string;
  timestamp_sim_min: number;
  anomaly_type: string;
  location: string;
  severity_score: number;
  description: string;
}

export interface SimulationStepState {
  tick: number;
  elapsed_sim_minutes: number;
  is_running: boolean;
  speed_multiplier: number;
  total_at_risk_population: number;
  total_evacuated: number;
  total_in_transit: number;
  evacuation_progress_pct: number;
  estimated_evacuation_time_minutes: number;
  baseline_eet_minutes: number;
  average_network_speed_kmh: number;
  active_bottlenecks_count: number;
  roads: RoadSegment[];
  shelters: ShelterHospital[];
  zones: EvacuationZone[];
  agents: EvacuationAgent[];
  predictions: Record<string, PredictionHorizonData>;
  advisories: TacticalAdvisory[];
  anomalies: AnomalyReport[];
  active_scenario: WhatIfScenario | null;
}

export interface ScenarioComparisonResult {
  baseline_eet_minutes: number;
  what_if_eet_minutes: number;
  time_delta_minutes: number;
  time_delta_pct: number;
  baseline_bottlenecks: number;
  what_if_bottlenecks: number;
  baseline_exposure_index: number;
  what_if_exposure_index: number;
  shelter_load_delta: Record<string, number>;
  recommendation: string;
}
