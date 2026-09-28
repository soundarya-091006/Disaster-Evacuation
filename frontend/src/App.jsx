import { useEffect, useState } from "react";
import MapView from "./MapView";
import { getDashboardStats } from "./api";
import "./App.css";

function App() {
  const [stats, setStats] = useState(null);

useEffect(() => {
  async function loadStats() {
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (error) {
      console.error(error);
    }
  }

  loadStats();
}, []);
  return (
    <div className="app">

      {/* Header */}
      <header className="header">
        <div>
          <h1>🚨 TwinEvac</h1>
          <p>Disaster Evacuation</p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          FLOOD • ACTIVE
        </div>
      </header>

      {/* Dashboard Cards */}
      <section className="stats">

        <div className="card">
          <div className="card-icon">🌊</div>
          <div>
            <h3>Disaster</h3>
            <p>Flood</p>
            <span>Severity: 75%</span>
          </div>
        </div>

        <div className="card">
          <div className="card-icon">🏠</div>
          <div>
            <h3>Shelters</h3>
            <p>3</p>
            <span>Active shelters</span>
          </div>
        </div>

        <div className="card">
          <div className="card-icon">🛣️</div>
          <div>
            <h3>Roads</h3>
            <p>3</p>
            <span>0 blocked</span>
          </div>
        </div>

        <div className="card">
          <div className="card-icon">👥</div>
          <div>
            <h3>Population</h3>
            <p>850</p>
            <span>In shelters</span>
          </div>
        </div>

      </section>

      {/* Main Content */}
      <main className="main-content">

        <section className="map-section">

          <div className="section-header">
            <div>
              <h2>Live Disaster Map</h2>
              <p>Real-time digital twin visualization</p>
            </div>

            <div className="map-status">
              ● LIVE
            </div>
          </div>

          <MapView />

        </section>

      </main>

    </div>
  );
}

export default App;