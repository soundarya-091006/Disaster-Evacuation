import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  Polygon
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import {
  getShelters,
  getRoads,
  getDisasterZones
} from "./api";

function MapView() {
  const [shelters, setShelters] = useState([]);
  const [roads, setRoads] = useState([]);
  const [disasterZones, setDisasterZones] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const [
          shelterData,
          roadData,
          disasterData
        ] = await Promise.all([
          getShelters(),
          getRoads(),
          getDisasterZones()
        ]);

        setShelters(shelterData);
        setRoads(roadData);
        setDisasterZones(disasterData);

      } catch (err) {
        console.error(err);
        setError("Failed to load TwinEvac data.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return <h2>Loading TwinEvac data...</h2>;
  }

  if (error) {
    return <h2>{error}</h2>;
  }

  return (
    <MapContainer
      center={[11.6665, 78.1480]}
      zoom={14}
      style={{
        height: "600px",
        width: "100%"
      }}
    >

      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* DISASTER ZONES */}
      {disasterZones.map((zone) => {
        const geojson = JSON.parse(zone.geometry);

        const coordinates = geojson.coordinates[0];

        const positions = coordinates.map(
          ([longitude, latitude]) => [
            latitude,
            longitude
          ]
        );

        return (
          <Polygon
            key={zone.id}
            positions={positions}
            pathOptions={{
              fillColor: "red",
              fillOpacity: 0.25,
              color: "red"
            }}
          >
            <Popup>
              <strong>🌊 {zone.disaster_type}</strong>
              <br />
              Severity: {zone.severity * 100}%
              <br />
              Status: {zone.is_active ? "Active" : "Inactive"}
            </Popup>
          </Polygon>
        );
      })}

      {/* ROADS */}
      {roads.map((road) => {
        const geojson = JSON.parse(road.geometry);

        const positions = geojson.coordinates.map(
          ([longitude, latitude]) => [
            latitude,
            longitude
          ]
        );

        return (
          <Polyline
            key={road.id}
            positions={positions}
            pathOptions={{
              color: road.is_blocked ? "red" : "blue",
              weight: 5
            }}
          >
            <Popup>
              <strong>🛣️ {road.name}</strong>
              <br />
              Capacity: {road.capacity}
              <br />
              Status:{" "}
              {road.is_blocked
                ? "🚫 Blocked"
                : "✅ Open"}
            </Popup>
          </Polyline>
        );
      })}

      {/* SHELTERS */}
      {shelters.map((shelter) => (
        <Marker
          key={shelter.id}
          position={[
            shelter.latitude,
            shelter.longitude
          ]}
        >
          <Popup>
            <strong>🏠 {shelter.name}</strong>
            <br />
            Capacity: {shelter.capacity}
            <br />
            Current Population:{" "}
            {shelter.current_population}
            <br />
            Available:{" "}
            {shelter.capacity -
              shelter.current_population}
            <br />
            Status:{" "}
            {shelter.is_open
              ? "🟢 Open"
              : "🔴 Closed"}
          </Popup>
        </Marker>
      ))}

    </MapContainer>
  );
}

export default MapView;