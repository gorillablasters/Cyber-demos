import React, { useEffect, useState } from "react";
import DoomHeader from "../components/DoomHeader";
import SystemGrid from "../components/SystemGrid";
import SatPanel from "../components/SatPanel";
import LogConsole from "../components/LogConsole";
import { apiGet } from "../lib/api";

export default function Dashboard() {
  const [world, setWorld] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);

  async function pull() {
    const w = await apiGet<any>("/api/sim/world");
    if (w.ok) setWorld(w.world);

    const e = await apiGet<any>("/api/sim/events");
    if (e.ok) setEvents(e.events);
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
          <div key={s.sat_id} style={{ gridColumn: "span 3" }}>
            <SatPanel sat={s} />
          </div>
        ))}

        <div style={{ gridColumn: "span 6" }}>
          <div className="panelTitle">SYSTEM LOG</div>
          <LogConsole events={events} />
        </div>
      </SystemGrid>
    </>
  );
}
