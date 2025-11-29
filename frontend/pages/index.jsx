// frontend/pages/index.jsx
import React, { useState, useEffect } from "react";

/* Flags for stages 1–6 */
const EXPECTED_FLAGS = [
  "DOOM{There's}",
  "DOOM{only}",
  "DOOM{one}",
  "DOOM{beer}",
  "DOOM{left}",
  "DOOM{doomsday_sequence_complete}",
];

export default function Home() {
  const [history, setHistory] = useState([
    "███╗   ███╗ █████╗ ███████╗██╗  ██╗",
    "████╗ ████║██╔══██╗██╔════╝██║ ██╔╝",
    "██╔████╔██║███████║███████╗█████╔╝ ",
    "██║╚██╔╝██║██╔══██║╚════██║██╔═██╗ ",
    "██║ ╚═╝ ██║██║  ██║███████║██║  ██╗",
    "╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
    "       TOP SECRET // DOOMCORE",
    "",
    "OPERATION DOOMSDAY // GROUNDSTATION MF-01",
    "Link Status: [ESTABLISHED]",
    "",
    "Type `help` to list available commands."
  ]);

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastHex, setLastHex] = useState(null);

  const backendBase =
    process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const [flagInput, setFlagInput] = useState("");
  const [flagStatus, setFlagStatus] = useState("");
  const [foundFlags, setFoundFlags] = useState([]);
  const [doomsdayActive, setDoomsdayActive] = useState(false);

  const totalFlags = EXPECTED_FLAGS.length;
  const flagProgress = (foundFlags.length / totalFlags) * 100;

  const [orbitInfo, setOrbitInfo] = useState({ lat: 0, lon: 0 });

  const [fwFile, setFwFile] = useState(null);
  const [fwStatus, setFwStatus] = useState("");

  // const MAX_LINE_LEN = 44;

  // const chunkLine = (line) => {
  //   if (typeof line !== "string") return [];
  //   if (line.length <= MAX_LINE_LEN) return [line];
  //   const out = [];
  //   for (let i = 0; i < line.length; i += MAX_LINE_LEN) {
  //     out.push(line.slice(i, i + MAX_LINE_LEN));
  //   }
  //   return out;
  // };

  const flickerScreen = () => {
    if (typeof document === "undefined") return;
    const el = document.body;
    el.style.filter = "brightness(1.35) contrast(1.3)";
    setTimeout(() => {
      el.style.filter = "";
    }, 160);
  };

  // const pushLine = (line) => {
  //   if (typeof line !== "string") return;
  //   const chunks = chunkLine(line);
  //   flickerScreen();
  //   setHistory((h) => [...h, ...chunks]);
  // };
  const pushLine = (line) => {
  if (typeof line !== "string") return;
  flickerScreen();
  setHistory((h) => [...h, line]);
};


  const handleKeyDown = (e) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(commandHistory[commandHistory.length - 1 - newIndex]);
      } else {
        setHistoryIndex(-1);
        setInput("");
      }
    }
  };

  const handleFlagSubmit = (e) => {
    e.preventDefault();
    const raw = flagInput.trim();
    if (!raw) return;

    const normalized = raw;
    if (EXPECTED_FLAGS.includes(normalized)) {
      if (!foundFlags.includes(normalized)) {
        setFoundFlags((prev) => [...prev, normalized]);
        setFlagStatus("✅ Correct flag registered.");
        pushLine(`[FLAG] Accepted: ${normalized}`);
      } else {
        setFlagStatus("ℹ️ Flag already submitted.");
      }
    } else {
      setFlagStatus("❌ Invalid flag.");
      pushLine(`[FLAG] Rejected: ${normalized}`);
    }
    setFlagInput("");
  };

  useEffect(() => {
    if (!doomsdayActive && foundFlags.length === totalFlags) {
      setDoomsdayActive(true);
      pushLine("=== DOOMSDAY SEQUENCE COMPLETE ===");
      pushLine("DOOMSDAY LASER: TARGET LOCKED.");
      pushLine("EARTH: MASK OFF.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [foundFlags, totalFlags, doomsdayActive]);

  useEffect(() => {
    const timer = setInterval(() => {
      const t = Date.now() / 1000;
      const orbitalPeriod = 92 * 60;
      const phase = (t % orbitalPeriod) / orbitalPeriod;
      const lat = Math.sin(phase * 2 * Math.PI) * 45;
      const lon = phase * 360 - 180;
      setOrbitInfo({ lat, lon });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const messages = [
      "[ALERT] Mask resonance spike detected.",
      "[WARN] Villain coolant below nominal.",
      "[ALERT] Hero comms intercepted. Scrambling mask.",
      "[WARN] Beam jitter detected.",
      "[INFO] Latent DOOM energy in orbit."
    ];
    let active = true;
    const loop = () => {
      const delay = 45000 + Math.random() * 30000;
      setTimeout(() => {
        if (!active) return;
        const msg = messages[Math.floor(Math.random() * messages.length)];
        pushLine(msg);
        loop();
      }, delay);
    };
    loop();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const line = input.trim();
    if (!line) return;

    pushLine(`> ${line}`);
    setInput("");
    setCommandHistory((h) => [...h, line]);
    setHistoryIndex(-1);

    if (busy) {
      pushLine("[WAIT] Command in progress...");
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
        pushLine(`[ERR] ${data.error}`);
      } else {
        if (data.text) {
          pushLine("=== DECODED TEXT ===");
          // data.text.split(/\n/).forEach((ln) => pushLine(ln));
          data.text.split(/\n/).forEach((ln) => {
  if (ln.trim().length > 0) pushLine(ln);
});

        }
        if (data.raw_hex) setLastHex(data.raw_hex);
      }
    } catch (err) {
      pushLine(`[ERR] ${err.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleFirmwareUpload = async () => {
    if (!fwFile) return;
    const form = new FormData();
    form.append("file", fwFile);
    try {
      const res = await fetch(`${backendBase}/api/upload_firmware`, {
        method: "POST",
        body: form
      });
      const data = await res.json();
      if (!data.ok) {
        setFwStatus("❌ Upload error");
        pushLine(`[FW] ERROR: ${data.error}`);
      } else {
        setFwStatus("✅ Firmware uploaded");
        pushLine("=== FIRMWARE RESPONSE ===");
        data.text.split(/\n/).forEach((ln) => pushLine(ln));
      }
    } catch (err) {
      setFwStatus("❌ Upload failed.");
      pushLine(`[FW] Upload failed: ${err.message}`);
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
          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
        padding: "24px",
        position: "relative",
        overflow: "hidden"
      }}
    >
      {/* Strong CRT scanlines */}
      <div
        style={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(rgba(255,255,255,0.20) 3px, rgba(0,0,0,0) 3px)",
          backgroundSize: "100% 4px",
          mixBlendMode: "overlay",
          animation: "scan 9s linear infinite"
        }}
      ></div>

      <style jsx global>{`
        @keyframes scan {
          0% {
            transform: translateY(-100%);
          }
          100% {
            transform: translateY(100%);
          }
        }
      `}</style>

      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <header style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: "1.8rem", marginBottom: 4 }}>
            {doomsdayActive ? "DOOMSDAY LASER ONLINE" : "OPERATION DOOMSDAY"}
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
          {/* Terminal */}
          <section
            style={{
              background: "rgba(10, 10, 10, 0.9)",
              borderRadius: 12,
              border: "1px solid #552222",
              boxShadow: doomsdayActive
                ? "0 0 32px rgba(255, 0, 0, 0.8)"
                : "0 0 24px rgba(200, 0, 0, 0.4)",
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
                background:
                  "linear-gradient(90deg, rgba(120,0,0,0.5), rgba(40,0,0,0.4))"
              }}
            >
              DOOMCORE GROUNDSTATION CONSOLE
            </div>

            <div
              style={{
                flex: 1,
                padding: "12px",
                overflowY: "auto",
                fontSize: "0.85rem",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all"
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
              <span style={{ color: "#ff4444" }}>mf@doomcore:~$ █</span>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
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
                placeholder="type 'help', 'dump 0 512', 'fw_info', 'leak'..."
              />
              <button
                type="submit"
                disabled={busy}
                style={{
                  background: busy ? "#552222" : "#aa2222",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 10px",
                  cursor: busy ? "not-allowed" : "pointer",
                  color: "#f5f5f5"
                }}
              >
                {busy ? "..." : "SEND"}
              </button>
            </form>
          </section>

          {/* Sidebar */}
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
            {/* Orbit */}
            <div>
              <h3>DOOMSAT-1 LIVE ORBIT</h3>
              <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                LAT: {orbitInfo.lat.toFixed(2)}°
              </div>
              <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                LON: {orbitInfo.lon.toFixed(2)}°
              </div>
            </div>

            {/* Laser progress */}
            <div>
              <h3>DOOMSDAY LASER PROGRESS</h3>
              <div
                style={{
                  height: 8,
                  borderRadius: 999,
                  background: "#220000",
                  overflow: "hidden",
                  marginTop: 6
                }}
              >
                <div
                  style={{
                    width: `${flagProgress}%`,
                    height: "100%",
                    background:
                      "linear-gradient(90deg, #33ff88, #ffee33, #ff3333)",
                    transition: "width 0.4s"
                  }}
                ></div>
              </div>
              <div style={{ fontSize: "0.75rem", opacity: 0.8, marginTop: 4 }}>
                Flags found: {foundFlags.length} / {totalFlags}
              </div>
            </div>

            {/* Flag input */}
            <div>
              <h3>Submit Flag</h3>
              <form
                onSubmit={handleFlagSubmit}
                style={{ display: "flex", flexDirection: "column", gap: 6 }}
              >
                <input
                  value={flagInput}
                  onChange={(e) => setFlagInput(e.target.value)}
                  placeholder="DOOM{...}"
                  style={{
                    background: "#111",
                    border: "1px solid #333",
                    borderRadius: 6,
                    color: "#f5f5f5",
                    padding: "4px 8px"
                  }}
                />
                <button
                  type="submit"
                  style={{
                    background: "#225522",
                    border: "none",
                    borderRadius: 6,
                    padding: "4px 8px",
                    color: "#f5f5f5"
                  }}
                >
                  Submit
                </button>
              </form>
              {flagStatus && (
                <div style={{ fontSize: "0.75rem", marginTop: 4 }}>
                  {flagStatus}
                </div>
              )}
            </div>

            {/* Quick actions */}
            <div>
              <h3>Quick Actions</h3>
              <button onClick={() => setInput("leak")} style={quickButtonStyle}>
                Trigger Memory Leak
              </button>
              <button
                onClick={() => setInput("dump 0 2048")}
                style={quickButtonStyle}
              >
                Dump Flash [0x0000..0x0800]
              </button>
              <button
                onClick={() => setInput("fw_info")}
                style={quickButtonStyle}
              >
                Firmware Update Hints
              </button>
            </div>

            {/* Firmware upload */}
            <div>
              <h3>Upload Firmware</h3>
              <input
                type="file"
                onChange={(e) => setFwFile(e.target.files[0])}
                style={{
                  background: "#111",
                  color: "#ddd",
                  border: "1px solid #333",
                  borderRadius: 6,
                  padding: 4,
                  fontSize: "0.75rem"
                }}
              />
              <button
                onClick={handleFirmwareUpload}
                style={{
                  marginTop: 6,
                  background: "#4444aa",
                  border: "none",
                  borderRadius: 6,
                  padding: "4px 8px",
                  color: "white",
                  cursor: "pointer",
                  fontSize: "0.8rem"
                }}
              >
                Upload
              </button>
              {fwStatus && (
                <div style={{ marginTop: 4, fontSize: "0.75rem" }}>
                  {fwStatus}
                </div>
              )}
            </div>

            {/* Hex preview */}
            {lastHex && (
              <div>
                <h3>Last Raw Hex</h3>
                <div
                  style={{
                    background: "#050505",
                    borderRadius: 6,
                    border: "1px solid #333",
                    padding: 8,
                    maxHeight: 160,
                    overflowY: "auto",
                    fontSize: "0.7rem",
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
