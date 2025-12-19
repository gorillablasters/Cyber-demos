import { useState } from "react";
import { apiPost } from "../lib/api";
export default function CommandConsole() {
  const [hex, setHex] = useState("");
  const [resp, setResp] = useState(null);

  async function send() {
    const r = await apiPost<any>("/api/sim/uplink", JSON.stringify({ frame_hex: hex }));
    setResp(await r.json());
  }

  return (
    <div>
      <div style={{ marginBottom: "10px" }}>Uplink Frame Hex:</div>
      <input
        style={{ width: "100%", background: "#002200", color: "#00ff66" }}
        value={hex}
        onChange={(e) => setHex(e.target.value)}
      />

      <button
        style={{ marginTop: "10px" }}
        onClick={send}
      >
        SEND
      </button>

      {resp && <pre>{JSON.stringify(resp, null, 2)}</pre>}
    </div>
  );
}
