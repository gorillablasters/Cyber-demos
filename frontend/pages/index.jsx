
import React, { useState } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([
    "OPERATION DOOMSDAY // GROUNDSTATION MF-01",
    "Link Status: [ESTABLISHED]",
    "Villain: MF DOOM // Codename: DOOMCORE",
    "",
    "Type `help` to list available commands."
  ]);
  const [busy, setBusy] = useState(false);
  const [lastHex, setLastHex] = useState(null);

  const backendBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const pushLine = (line) => {
    setHistory((h) => [...h, line]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const line = input.trim();
    if (!line) return;
    pushLine(`> ${line}`);
    setInput("");
    if (busy) {
      pushLine("[WAIT] Command in flight...");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch(`${backendBase}/api/cmd`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ line })
      });
      const data = await res.json();
      if (!data.ok) {
        pushLine(`[ERR] ${data.error || "unknown error"}`);
      } else {
        if (data.text && data.text.trim().length > 0) {
          pushLine("=== DECODED TEXT ===");
          data.text.split(/\r?\n/).forEach((ln) => pushLine(ln));
        }
        if (data.raw_hex && data.raw_hex.length > 0) {
          pushLine("=== RAW HEX (truncated) ===");
          pushLine(
            data.raw_hex.slice(0, 200) +
              (data.raw_hex.length > 200 ? "..." : "")
          );
          setLastHex(data.raw_hex);
        }
      }
    } catch (err) {
      pushLine(`[ERR] ${err.message || String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  const quickButtonStyle = {
    background: "#331111",
    border: "1px solid #662222",
    borderRadius: 6,
    padding: "6px 8px",
    fontSize: "0.8rem",
    cursor: "pointer",
    color: "#f5f5f5",
    textAlign: "left"
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top, #441111 0, #050505 55%, #000000 100%)",
        color: "#f5f5f5",
        fontFamily:
          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        padding: "24px"
      }}
    >
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <header style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: "1.8rem", marginBottom: 4 }}>
            OPERATION DOOMSDAY
          </h1>
          <div style={{ fontSize: "0.9rem", opacity: 0.8 }}>
            MF DOOM // DOOMSAT CONTROL // VILLAIN FREQUENCY
          </div>
        </header>

        <div
          style={{
            display: "grid",
            gap: "16px",
            gridTemplateColumns: "2fr 1fr"
          }}
        >
          <section
            style={{
              background: "rgba(10, 10, 10, 0.9)",
              borderRadius: 12,
              border: "1px solid #552222",
              boxShadow: "0 0 24px rgba(200, 0, 0, 0.4)",
              display: "flex",
              flexDirection: "column",
              minHeight: "60vh"
            }}
          >
            <div
              style={{
                padding: "8px 12px",
                borderBottom: "1px solid #552222",
                fontSize: "0.85rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background:
                  "linear-gradient(90deg, rgba(120,0,0,0.7), rgba(40,0,0,0.4))"
              }}
            >
              <span>DOOMCORE GROUNDSTATION CONSOLE</span>
              <span style={{ color: "#ff6666" }}>
                LINK: <strong>ONLINE</strong>
              </span>
            </div>
            <div
              style={{
                flex: 1,
                padding: "12px",
                overflowY: "auto",
                fontSize: "0.85rem",
                whiteSpace: "pre-wrap"
              }}
            >
              {history.map((line, idx) => (
                <div key={idx}>{line}</div>
              ))}
            </div>
            <form
              onSubmit={handleSubmit}
              style={{
                borderTop: "1px solid #552222",
                padding: "8px 12px",
                display: "flex",
                gap: 8,
                alignItems: "center"
              }}
            >
              <span style={{ color: "#ff4444" }}>mf@doomcore:~$</span>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                style={{
                  flex: 1,
                  background: "#111",
                  border: "1px solid #333",
                  borderRadius: 6,
                  color: "#f5f5f5",
                  fontSize: "0.9rem",
                  padding: "4px 8px"
                }}
                autoFocus
                placeholder="type 'help', 'dump 0 512', 'leak', 'fw_info'..."
              />
              <button
                type="submit"
                disabled={busy}
                style={{
                  background: busy ? "#552222" : "#aa2222",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 10px",
                  fontSize: "0.8rem",
                  cursor: busy ? "not-allowed" : "pointer",
                  color: "#f5f5f5"
                }}
              >
                {busy ? "..." : "SEND"}
              </button>
            </form>
          </section>

          <section
            style={{
              background: "#080808",
              borderRadius: 12,
              border: "1px solid #552222",
              padding: 12,
              display: "flex",
              flexDirection: "column",
              gap: 12
            }}
          >
            <div>
              <h2 style={{ fontSize: "1rem", marginBottom: 4 }}>
                DOOMSAT-1 STATUS
              </h2>
              <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                ORBIT: LEO / MASK ALIGNMENT: NOMINAL / VILLAIN MODE: ENABLED
              </div>
              <div
                style={{
                  marginTop: 8,
                  height: 6,
                  borderRadius: 999,
                  background: "#220000",
                  overflow: "hidden"
                }}
              >
                <div
                  style={{
                    width: "82%",
                    height: "100%",
                    background:
                      "linear-gradient(90deg, #33ff88, #ffee33, #ff3333)"
                  }}
                ></div>
              </div>
              <div
                style={{
                  fontSize: "0.7rem",
                  marginTop: 4,
                  opacity: 0.7
                }}
              >
                Signal Integrity: 82% // DOOMSDAY BEAM: STANDBY
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: "0.9rem", marginBottom: 4 }}>
                Quick Actions
              </h3>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6
                }}
              >
                <button
                  onClick={() => setInput("leak")}
                  style={quickButtonStyle}
                >
                  Trigger Memory Leak
                </button>
                <button
                  onClick={() => setInput("dump 0 512")}
                  style={quickButtonStyle}
                >
                  Dump Flash [0x0000..0x0200]
                </button>
                <button
                  onClick={() => setInput("fw_info")}
                  style={quickButtonStyle}
                >
                  Firmware Update Hints
                </button>
              </div>
            </div>

            {lastHex && (
              <div style={{ marginTop: 8 }}>
                <h3 style={{ fontSize: "0.9rem", marginBottom: 4 }}>
                  Last Raw Hex (preview)
                </h3>
                <div
                  style={{
                    fontSize: "0.7rem",
                    maxHeight: 160,
                    overflowY: "auto",
                    background: "#050505",
                    borderRadius: 8,
                    border: "1px solid #333",
                    padding: 8,
                    wordBreak: "break-all"
                  }}
                >
                  {lastHex}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
