import { apiPost } from "../lib/api";
import DoomHeader from "../components/DoomHeader";
import HexViewer from "../components/HexViewer";
import { useEffect, useState } from "react";
import SystemGrid from "../components/SystemGrid";

export default function HexPage() {
  const [inbox, setInbox] = useState<any[]>([]);
  const [sat, setSat] = useState(0x11);

  async function pull() {
    const r = await apiPost<any>("/api/sim/crosslink/dump", JSON.stringify({ sat_id: sat, max_frames: 50 }));
    const j = await r.json();
    if (j.ok) setInbox(j.frames);
  }

  useEffect(() => {
    pull();
    const t = setInterval(pull, 1200);
    return () => clearInterval(t);
  }, [sat]);

  return (
    <>
      <DoomHeader />
      <SystemGrid>
        <div style={{ gridColumn: "span 12" }}>
          <h3>Crosslink Inbox for {sat.toString(16)}</h3>

          <select
            style={{ background: "#003300", color: "#00ff66" }}
            onChange={(e) => setSat(parseInt(e.target.value))}
          >
            <option value={0x11}>K00KIES-01</option>
            <option value={0x12}>K00KIES-02</option>
            <option value={0x01}>D00M-01</option>
            <option value={0x02}>D00M-02</option>
          </select>
        </div>

        <div style={{ gridColumn: "span 12" }}>
          {inbox.map((f, i) => (
            <div key={i} style={{ marginBottom: "20px" }}>
              <div>From: {f.src_sat_id}</div>
              <div>To: {f.dst_sat_id ?? "Broadcast"}</div>
              <HexViewer data={f.payload_hex} />
            </div>
          ))}
        </div>
      </SystemGrid>
    </>
  );
}
