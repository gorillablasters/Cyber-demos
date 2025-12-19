import DoomHeader from "../components/DoomHeader";
import CrosslinkMap from "../components/CrosslinkMap";
import CommandConsole from "../components/CommandConsole";
import SystemGrid from "../components/SystemGrid";
import React, { useEffect, useState } from "react";
import { apiGet } from "../lib/api";

export default function Crosslink() {
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
