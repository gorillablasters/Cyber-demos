import { useState } from "react";
import { apiPost } from "../lib/api";

export default function FirmwareConsole({ sat_id }: { sat_id: number }) {
  const [hex, setHex] = useState("");
  const [claimed, setClaimed] = useState("");
  const [resp, setResp] = useState<any>(null);

  async function upload() {
    const r = await apiPost<any>("/api/sim/firmware/upload", JSON.stringify({ sat_id, chunk_hex: hex }));
    setResp(await r.json());
  }

  async function applyFw() {
    const r = await apiPost<any>("/api/sim/firmware/apply", JSON.stringify({ sat_id, claimed_hash: claimed }));
    setResp(await r.json());
  }

  return (
    <div>
      <h4>Upload Chunk</h4>
      <textarea
        style={{ width: "100%", height: "60px", background: "#002200", color: "#00ff66" }}
        value={hex}
        onChange={(e) => setHex(e.target.value)}
      />

      <button onClick={upload}>UPLOAD</button>

      <h4>Apply Firmware</h4>
      <input
        style={{ width: "100%", background: "#002200", color: "#00ff66" }}
        value={claimed}
        onChange={(e) => setClaimed(e.target.value)}
      />

      <button onClick={applyFw}>APPLY</button>

      {resp && <pre>{JSON.stringify(resp, null, 2)}</pre>}
    </div>
  );
}
