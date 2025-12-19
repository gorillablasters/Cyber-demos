import DoomHeader from "../components/DoomHeader";
import FirmwareConsole from "../components/FirmwareConsole";
import React, { useEffect, useState } from "react";
import SystemGrid from "../components/SystemGrid";
import { apiGet } from "../lib/api";

export default function FirmwarePage() {
  const [world, setWorld] = useState<any>(null);
  const [sat, setSat] = useState<number>(1);

  async function pull() {
    const j = await apiGet<any>("/api/sim/world");
    if (j.ok) setWorld(j.world);
  }

  useEffect(() => {
    pull();
    const t = setInterval(pull, 1000);
    return () => clearInterval(t);
  }, []);

  if (!world) return <>Loading...</>;

  return (
    <>
      <DoomHeader />
      <SystemGrid>
        <div style={{ gridColumn: "span 12" }}>
          <div className="panelTitle">SELECT SATELLITE</div>
          <select value={sat} onChange={(e) => setSat(parseInt(e.target.value, 10))}>
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
