import DoomHeader from "../components/DoomHeader";
import CrosslinkMap from "../components/CrosslinkMap";
import CommandConsole from "../components/CommandConsole";
import SystemGrid from "../components/SystemGrid";
import React, { useEffect, useState } from "react";
const API = "http://localhost:8000";
export default function Crosslink() {
  const [world, setWorld] = useState<any>(null);

  async function pull() {
    const r = await fetch(`${API}/api/sim/world`);
    const j = await r.json();
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
          <CrosslinkMap sats={world.satellites} />
        </div>

        <div style={{ gridColumn: "span 12" }}>
          <CommandConsole />
        </div>
      </SystemGrid>
    </>
  );
}
