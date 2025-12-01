import { useState } from "react";
const API = "http://localhost:8000";
export default function CommandConsole() {
  const [hex, setHex] = useState("");
  const [resp, setResp] = useState(null);

  async function send() {
    const r = await fetch(`${API}/api/sim/uplink`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frame_hex: hex }),
    });
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
