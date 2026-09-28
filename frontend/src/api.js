const API_URL = "http://127.0.0.1:8000";

export async function getShelters() {
  const response = await fetch(`${API_URL}/shelters`);

  if (!response.ok) {
    throw new Error("Failed to fetch shelters");
  }

  return response.json();
}

export async function getRoads() {
  const response = await fetch(`${API_URL}/roads`);

  if (!response.ok) {
    throw new Error("Failed to fetch roads");
  }

  return response.json();
}

export async function getDisasterZones() {
  const response = await fetch(`${API_URL}/disaster-zones`);

  if (!response.ok) {
    throw new Error("Failed to fetch disaster zones");
  }

  return response.json();
}