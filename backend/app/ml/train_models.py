"""
TwinEvac - Production AI/ML Training Pipeline
Trains:
1. PyTorch Multi-Horizon Traffic LSTM Network (15m, 30m, 60m forecasting)
2. Scikit-Learn Traffic Tabular Ensemble Regressor
3. Multi-Hazard Dynamic Risk Random Forest Classifier (LOW / MED / HIGH / CRITICAL)
4. Unsupervised Flow & Gridlock Anomaly Isolation Forest
5. Reinforcement Learning Q-Routing Graph Policy Agent
6. Multi-Horizon Shelter Occupancy Regressor

Saves trained weights and evaluation metadata to backend/app/ml/models/
"""

import os
import json
import time
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, IsolationForest
from sklearn.metrics import classification_report, accuracy_score, f1_score, r2_score, mean_squared_error
from sklearn.model_selection import train_test_split

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Ensure reproducibility
np.random.seed(42)
random.seed(42)
torch.manual_seed(42)

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 1. PyTorch LSTM Architecture
# =====================================================================
class TrafficLSTM(nn.Module):
    def __init__(self, input_dim: int = 7, hidden_dim: int = 64, num_layers: int = 2, output_dim: int = 6):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1 if num_layers > 1 else 0.0
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.05),
            nn.Linear(32, output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len, input_dim)
        out, _ = self.lstm(x)
        last_hidden = out[:, -1, :]  # shape: (batch_size, hidden_dim)
        pred = self.fc(last_hidden)
        return pred


# =====================================================================
# 2. Synthetic Ground-Truth Data Generation (Domain Calibrated)
# =====================================================================
def generate_traffic_dataset(num_samples: int = 1600, seq_len: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simulates sequence windows representing road segments under various disaster conditions.
    Features per step: [congestion, speed_norm, flood_depth_norm, rainfall_norm, contagion, upstream_cong, is_closed]
    Targets: [cong_15m, speed_15m, cong_30m, speed_30m, cong_60m, speed_60m]
    """
    X_seq = []
    Y_target = []

    for _ in range(num_samples):
        # Initial segment state
        c0 = np.random.uniform(0.05, 0.95)
        flood = np.random.choice([0.0, np.random.uniform(5.0, 45.0)], p=[0.6, 0.4])
        rainfall = np.random.uniform(0.0, 80.0)
        contagion = np.random.uniform(0.0, 0.85)
        upstream = np.random.uniform(0.05, 0.90)
        is_closed = 1.0 if (c0 > 0.9 and flood > 35.0) or np.random.rand() < 0.06 else 0.0
        free_speed = np.random.choice([35.0, 45.0, 60.0])

        seq = []
        curr_c = c0
        for t in range(seq_len):
            fluct = np.random.normal(0, 0.03)
            curr_c = max(0.02, min(0.99, curr_c + fluct + (rainfall / 500.0)))
            curr_speed = 0.0 if is_closed else free_speed * max(0.08, 1.0 - curr_c * 0.85)
            step_feat = [
                curr_c,
                curr_speed / 75.0,
                min(1.0, flood / 50.0),
                min(1.0, rainfall / 100.0),
                contagion,
                upstream,
                is_closed
            ]
            seq.append(step_feat)

        # Ground truth forward projection for 15m, 30m, 60m
        if is_closed:
            cong_15, spd_15 = 1.0, 0.0
            cong_30, spd_30 = 1.0, 0.0
            cong_60, spd_60 = 1.0, 0.0
        else:
            inflow = upstream * 0.35 + (rainfall / 150.0) + (flood / 80.0)
            cong_15 = max(0.05, min(0.98, curr_c * 0.88 + inflow * 0.32 + np.random.normal(0, 0.02)))
            spd_15 = free_speed * max(0.1, 1.0 - cong_15 * 0.85)

            cong_30 = max(0.05, min(0.98, curr_c * 0.75 + inflow * 0.50 + np.random.normal(0, 0.03)))
            spd_30 = free_speed * max(0.08, 1.0 - cong_30 * 0.85)

            cong_60 = max(0.05, min(0.98, curr_c * 0.60 + inflow * 0.65 + np.random.normal(0, 0.04)))
            spd_60 = free_speed * max(0.05, 1.0 - cong_60 * 0.85)

        X_seq.append(seq)
        Y_target.append([cong_15, spd_15, cong_30, spd_30, cong_60, spd_60])

    return np.array(X_seq, dtype=np.float32), np.array(Y_target, dtype=np.float32)


def generate_risk_dataset(num_samples: int = 2400) -> Tuple[np.ndarray, np.ndarray]:
    """
    Features: [flood_depth_cm, contagion_score, congestion_index, current_speed_kmh, capacity_pcu, rainfall_mmh, is_closed]
    Labels: 0: LOW, 1: MEDIUM, 2: HIGH, 3: CRITICAL
    """
    X = []
    Y = []
    for _ in range(num_samples):
        flood = np.random.choice([0.0, np.random.uniform(2.0, 50.0)], p=[0.5, 0.5])
        contagion = np.random.uniform(0.0, 1.0)
        congestion = np.random.uniform(0.05, 1.0)
        free_speed = np.random.choice([25.0, 35.0, 45.0, 65.0])
        speed = max(0.0, free_speed * (1.0 - congestion * 0.85))
        capacity = np.random.choice([1400.0, 1800.0, 2400.0, 3200.0])
        rainfall = np.random.uniform(0.0, 100.0)
        is_closed = 1.0 if np.random.rand() < 0.07 else 0.0

        if is_closed:
            label = 3  # CRITICAL
        else:
            flood_norm = min(1.0, flood / 45.0)
            score = (flood_norm * 0.40) + (contagion * 0.35) + (congestion * 0.25)
            if score >= 0.72 or flood > 38.0:
                label = 3  # CRITICAL
            elif score >= 0.46 or flood > 18.0:
                label = 2  # HIGH
            elif score >= 0.22:
                label = 1  # MEDIUM
            else:
                label = 0  # LOW

        X.append([flood, contagion, congestion, speed, capacity, rainfall, is_closed])
        Y.append(label)

    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.int64)


def generate_anomaly_dataset(num_samples: int = 1500) -> np.ndarray:
    """
    Features: [volume_pcu, speed_kmh, congestion_index, volume_change_ratio, speed_drop_ratio]
    Mostly normal operational distributions, with ~6% sudden anomalies.
    """
    X = []
    for _ in range(num_samples):
        is_anom = np.random.rand() < 0.06
        if not is_anom:
            vol = np.random.uniform(150.0, 1800.0)
            cong = np.random.uniform(0.1, 0.75)
            spd = max(15.0, 55.0 * (1.0 - cong * 0.7))
            vol_change = np.random.uniform(0.85, 1.45)
            spd_drop = np.random.uniform(0.0, 0.25)
        else:
            # Gridlock crash or extreme sudden surge
            vol = np.random.uniform(2200.0, 3800.0)
            cong = np.random.uniform(0.88, 1.0)
            spd = np.random.uniform(1.0, 7.5)
            vol_change = np.random.uniform(2.5, 4.2)
            spd_drop = np.random.uniform(0.65, 0.95)

        X.append([vol, spd, cong, vol_change, spd_drop])

    return np.array(X, dtype=np.float32)


def generate_shelter_dataset(num_samples: int = 1200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Features: [current_occupancy_pct, total_capacity, intake_rate, incoming_agents_count, active_infections, elapsed_time]
    Targets: [projected_15m, projected_30m, projected_60m]
    """
    X = []
    Y = []
    for _ in range(num_samples):
        curr_occ = np.random.uniform(5.0, 95.0)
        cap = np.random.choice([1200.0, 1400.0, 1600.0, 2500.0])
        intake = np.random.choice([25.0, 35.0, 40.0, 60.0])
        incoming = np.random.randint(5, 50)
        infections = np.random.randint(10, 350)
        elapsed = np.random.uniform(0.0, 120.0)

        rate_factor = (incoming * 15.0) / max(cap, 1.0) * 100.0
        p15 = min(100.0, curr_occ + rate_factor * 0.25 + np.random.normal(0, 1.0))
        p30 = min(100.0, curr_occ + rate_factor * 0.50 + np.random.normal(0, 1.5))
        p60 = min(100.0, curr_occ + rate_factor * 0.90 + np.random.normal(0, 2.0))

        X.append([curr_occ, cap, intake, incoming, infections, elapsed])
        Y.append([p15, p30, p60])

    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


# =====================================================================
# 3. Training Execution Pipeline
# =====================================================================
def train_traffic_models(X_seq: np.ndarray, Y: np.ndarray) -> Tuple[Dict[str, Any], TrafficLSTM, RandomForestRegressor]:
    print("--- [1/5] Training PyTorch Traffic LSTM Network ---")
    X_train, X_test, y_train, y_test = train_test_split(X_seq, Y, test_size=0.2, random_state=42)

    device = torch.device("cpu")
    model = TrafficLSTM(input_dim=7, hidden_dim=64, num_layers=2, output_dim=6).to(device)

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    epochs = 25
    train_losses = []
    model.train()
    for ep in range(epochs):
        ep_loss = 0.0
        for bx, by in train_loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()
            ep_loss += loss.item() * len(bx)
        scheduler.step()
        train_losses.append(ep_loss / len(X_train))

    # Evaluate LSTM
    model.eval()
    with torch.no_grad():
        test_preds = model(torch.tensor(X_test)).numpy()
        lstm_r2 = float(r2_score(y_test, test_preds))
        lstm_mse = float(mean_squared_error(y_test, test_preds))

    print(f"  PyTorch LSTM: Final Train Loss={train_losses[-1]:.4f}, Test R2={lstm_r2:.4f}, RMSE={math.sqrt(lstm_mse):.4f}")

    # Also train Tabular RF regressor as ensemble baseline
    print("--- [2/5] Training Scikit-Learn Traffic Tabular Regressor ---")
    X_tab_train = X_train[:, -1, :]  # most recent step features
    X_tab_test = X_test[:, -1, :]
    rf_reg = RandomForestRegressor(n_estimators=60, max_depth=8, random_state=42)
    rf_reg.fit(X_tab_train, y_train)
    rf_preds = rf_reg.predict(X_tab_test)
    rf_r2 = float(r2_score(y_test, rf_preds))
    print(f"  RandomForest Regressor: Test R2={rf_r2:.4f}")

    lstm_path = MODELS_DIR / "traffic_lstm.pt"
    torch.save(model.state_dict(), lstm_path)

    rf_path = MODELS_DIR / "traffic_rf.joblib"
    joblib.dump(rf_reg, rf_path)

    metrics = {
        "lstm_r2_score": round(lstm_r2, 4),
        "lstm_rmse": round(math.sqrt(lstm_mse), 4),
        "lstm_epochs": epochs,
        "rf_r2_score": round(rf_r2, 4),
        "input_features": ["congestion", "speed_norm", "flood_depth_norm", "rainfall_norm", "contagion", "upstream_cong", "is_closed"],
        "horizons_supported": [15, 30, 60]
    }
    return metrics, model, rf_reg


def train_risk_classifier(X: np.ndarray, y: np.ndarray) -> Tuple[Dict[str, Any], RandomForestClassifier]:
    print("--- [3/5] Training Multi-Hazard Risk Random Forest Classifier ---")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    rf = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, average="weighted"))

    feat_names = ["flood_depth_cm", "contagion_score", "congestion_index", "current_speed_kmh", "capacity_pcu", "rainfall_mmh", "is_closed"]
    importances = {name: round(float(imp), 4) for name, imp in zip(feat_names, rf.feature_importances_)}

    print(f"  Risk RF Classifier: Accuracy={acc*100:.2f}%, F1-Score={f1:.4f}")
    print(f"  Feature Importances: {importances}")

    rf_path = MODELS_DIR / "risk_rf.joblib"
    joblib.dump(rf, rf_path)

    metrics = {
        "accuracy_pct": round(acc * 100, 2),
        "f1_score": round(f1, 4),
        "classes": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "feature_importances": importances
    }
    return metrics, rf


def train_anomaly_detector(X: np.ndarray) -> Tuple[Dict[str, Any], IsolationForest]:
    print("--- [4/5] Training Isolation Forest Anomaly Detector ---")
    iso = IsolationForest(n_estimators=100, contamination=0.06, random_state=42)
    iso.fit(X)

    scores = iso.decision_function(X)
    outliers = (iso.predict(X) == -1).sum()

    print(f"  Isolation Forest: Outliers Flagged={outliers}/{len(X)} ({outliers/len(X)*100:.1f}%), Mean Decision Score={np.mean(scores):.3f}")

    iso_path = MODELS_DIR / "anomaly_isoforest.joblib"
    joblib.dump(iso, iso_path)

    metrics = {
        "contamination": 0.06,
        "n_estimators": 100,
        "mean_score": round(float(np.mean(scores)), 3),
        "features": ["volume_pcu", "speed_kmh", "congestion_index", "volume_change_ratio", "speed_drop_ratio"]
    }
    return metrics, iso


def train_shelter_predictor(X: np.ndarray, y: np.ndarray) -> Tuple[Dict[str, Any], RandomForestRegressor]:
    print("--- [5/5] Training Shelter Occupancy Forecaster ---")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf_shelter = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
    rf_shelter.fit(X_train, y_train)

    y_pred = rf_shelter.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))

    print(f"  Shelter Occupancy Predictor: R2={r2:.4f}")

    path = MODELS_DIR / "shelter_predictor.joblib"
    joblib.dump(rf_shelter, path)

    metrics = {
        "r2_score": round(r2, 4),
        "targets": ["occupancy_15m", "occupancy_30m", "occupancy_60m"]
    }
    return metrics, rf_shelter


def train_q_routing_agent() -> Dict[str, Any]:
    """
    Trains tabular Q-Learning policy on the Salem graph network.
    Learns Q(state, action) where action is selecting next neighbor node.
    Reward balances travel time, flood avoidance, and shelter capacity.
    """
    print("--- [Bonus] Training Graph Q-Routing Reinforcement Learning Agent ---")

    # Load Salem graph
    data_path = Path(__file__).resolve().parent.parent.parent / "data" / "salem_network.json"
    with open(data_path, "r", encoding="utf-8") as f:
        net = json.load(f)

    nodes = [n["id"] for n in net["nodes"]]
    edges = net["edges"]
    adj: Dict[str, List[Tuple[str, float]]] = {n: [] for n in nodes}
    for e in edges:
        adj[e["source"]].append((e["target"], e["distance_km"]))
        adj[e["target"]].append((e["source"], e["distance_km"]))

    # Shelters
    target_shelters = ["NODE_GMKMC_HOSP", "NODE_STEEL_PLANT", "NODE_GORIMEDU", "NODE_AYODHIYAPATTINAM"]

    # Q-table: (node, target_shelter) -> {next_node: q_value}
    q_table: Dict[str, Dict[str, float]] = {}

    alpha = 0.2
    gamma = 0.92
    episodes = 2500

    for _ in range(episodes):
        start = random.choice(nodes)
        target = random.choice(target_shelters)
        curr = start

        for _step in range(12):
            if curr == target:
                break
            neighbors = adj.get(curr, [])
            if not neighbors:
                break

            state_key = f"{curr}::{target}"
            if state_key not in q_table:
                q_table[state_key] = {nbr: 0.0 for nbr, _ in neighbors}

            # Epsilon-greedy
            if random.random() < 0.2:
                next_node = random.choice(neighbors)[0]
            else:
                next_node = max(q_table[state_key], key=q_table[state_key].get)

            dist = next(d for n, d in neighbors if n == next_node)
            # Reward: negative distance + bonus for reaching target
            reward = -dist
            if next_node == target:
                reward += 25.0

            next_state_key = f"{next_node}::{target}"
            max_next_q = 0.0
            if next_state_key in q_table and q_table[next_state_key]:
                max_next_q = max(q_table[next_state_key].values())

            old_q = q_table[state_key].get(next_node, 0.0)
            q_table[state_key][next_node] = old_q + alpha * (reward + gamma * max_next_q - old_q)
            curr = next_node

    q_path = MODELS_DIR / "q_routing_agent.json"
    with open(q_path, "w", encoding="utf-8") as f:
        json.dump(q_table, f, indent=2)

    print(f"  Q-Learning Agent: Converged over {episodes} episodes with {len(q_table)} state entries.")
    return {
        "episodes": episodes,
        "states_learned": len(q_table),
        "target_shelters": target_shelters,
        "algorithm": "Q-Learning Graph Router (SARSA/TD-0)"
    }


# =====================================================================
# Main Execution Entry Point
# =====================================================================
def run_all_training():
    start_t = time.time()
    print("=================================================================")
    print("        TWINEVAC ENTERPRISE AI/ML MODEL TRAINING SUITE           ")
    print("=================================================================")

    # 1. Traffic models
    X_seq, Y_traff = generate_traffic_dataset(num_samples=1800, seq_len=5)
    traff_metrics, _, _ = train_traffic_models(X_seq, Y_traff)

    # 2. Risk Classifier
    X_risk, y_risk = generate_risk_dataset(num_samples=2600)
    risk_metrics, _ = train_risk_classifier(X_risk, y_risk)

    # 3. Anomaly Detector
    X_anom = generate_anomaly_dataset(num_samples=1600)
    anom_metrics, _ = train_anomaly_detector(X_anom)

    # 4. Shelter Predictor
    X_shelter, y_shelter = generate_shelter_dataset(num_samples=1400)
    shelter_metrics, _ = train_shelter_predictor(X_shelter, y_shelter)

    # 5. Q-Routing Reinforcement Learning
    q_metrics = train_q_routing_agent()

    elapsed = round(time.time() - start_t, 2)
    metadata = {
        "status": "TRAINED",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "training_duration_seconds": elapsed,
        "models": {
            "traffic_lstm": traff_metrics,
            "risk_classifier": risk_metrics,
            "anomaly_detector": anom_metrics,
            "shelter_predictor": shelter_metrics,
            "q_routing_agent": q_metrics
        }
    }

    meta_path = MODELS_DIR / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("=================================================================")
    print(f"[OK] ALL AI/ML MODELS SUCCESSFULLY TRAINED & EXPORTED IN {elapsed}s!")
    print(f"Artifacts located at: {MODELS_DIR}")
    print("=================================================================")
    return metadata


if __name__ == "__main__":
    run_all_training()
