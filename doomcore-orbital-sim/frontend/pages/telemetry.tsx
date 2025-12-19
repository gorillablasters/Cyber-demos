import DoomHeader from "../components/DoomHeader";
import SystemGrid from "../components/SystemGrid";
import TelemetryPanel from "../components/TelemetryPanel";
import React, { useEffect, useState } from "react";
import { apiGet } from "../lib/api";

export default function Telemetry() {
  const [world, setWorld] = useState<any>(null);

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
        {world.satellites.map((s: any) => (
          <div key={s.sat_id} style={{ gridColumn: "span 4" }}>
            <TelemetryPanel sat={s} />
          </div>
        ))}
      </SystemGrid>
    </>
  );
}
