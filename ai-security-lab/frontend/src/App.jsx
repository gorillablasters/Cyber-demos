import React, { useEffect, useState, useCallback } from "react";
import MissionControlDashboard from "./components/MissionControlDashboard";
import AttackConsole from "./components/AttackConsole";
import { api } from "./api/client";

export default function App() {
  const [missions, setMissions] = useState([]);
  const [signals, setSignals] = useState([]);
  const [defenses, setDefenses] = useState([]);
  const [score, setScore] = useState(0);
  const [kbDocCount, setKbDocCount] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [view, setView] = useState("dashboard");
  const [attackingMission, setAttackingMission] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getState();
      setMissions(data.missions);
      setSignals(data.signals);
      setDefenses(data.defenses);
      setScore(data.score);
      setSelectedId((prev) => prev || data.missions.find((m) => m.status === "active")?.id || data.missions[0]?.id);
      setError(null);
    } catch (err) {
      setError("Can't reach the backend. Is the Flask server running on port 5000?");
    }
  }, []);

  useEffect(() => {
    refresh();
    api.getKb().then((docs) => setKbDocCount(docs.length)).catch(() => {});
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleToggleDefense(id) {
    const result = await api.toggleDefense(id);
    setDefenses((prev) => prev.map((d) => (d.id === id ? result.defense : d)));
    setScore(result.score);
    refresh();
  }

  function handleLaunchMission(mission) {
    setAttackingMission(mission);
    setView("attack");
  }

  function handleBackToDashboard() {
    setView("dashboard");
    refresh();
  }

  function handleAttackResolved() {
    refresh();
  }

  if (error) {
    return (
      <div className="mc-root">
        <div className="mc-panel" style={{ padding: 20 }}>
          <div className="mc-eyebrow" style={{ marginBottom: 8 }}>Connection error</div>
          <div style={{ fontSize: 14 }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!missions.length) {
    return (
      <div className="mc-root">
        <div style={{ fontSize: 13, color: "var(--text-lo)" }}>Loading...</div>
      </div>
    );
  }

  if (view === "attack" && attackingMission) {
    return (
      <AttackConsole
        mission={attackingMission}
        defenses={defenses}
        onBack={handleBackToDashboard}
        onAttackResolved={handleAttackResolved}
      />
    );
  }

  return (
    <MissionControlDashboard
      missions={missions}
      signals={signals}
      defenses={defenses}
      score={score}
      selectedId={selectedId}
      onSelectMission={setSelectedId}
      onToggleDefense={handleToggleDefense}
      onLaunchMission={handleLaunchMission}
      kbDocCount={kbDocCount}
    />
  );
}
