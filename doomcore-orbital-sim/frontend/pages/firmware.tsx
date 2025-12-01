import DoomHeader from "../components/DoomHeader";
import FirmwareConsole from "../components/FirmwareConsole";
import React, { useEffect, useState } from "react";
import SystemGrid from "../components/SystemGrid";
const API = "http://localhost:8000";
export default function FirmwarePage() {
  const [world, setWorld] = useState<any>(null);
  const [sat, setSat] = useState<number>(1);

  async function pull() {
    const r = await fetch(`${API}/api/sim/world`);
    const j = await r.json();
    if (j.ok) setWorld(j.world);
  }

  useEffect(() => {
    pull();
  }, []);

  if (!world) return <>Loading...</>;

  return (
    <>
      <DoomHeader />
      <SystemGrid>
        <div style={{ gridColumn: "span 12" }}>
          <h3>Select Satellite</h3>
          <select
            value={sat}
            onChange={(e) => setSat(parseInt(e.target.value))}
            style={{ background: "#003300", color: "#00ff66" }}
          >
            {world.satellites.map((s: any) => (
              <option key={s.sat_id} value={s.sat_id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ gridColumn: "span 12" }}>
          <FirmwareConsole sat_id={sat} />
        </div>
      </SystemGrid>
    </>
  );
}
