import React, { useState, useEffect } from "react";

// 🏴 EXPECTED FLAGS – use the ones from your file
const EXPECTED_FLAGS = [
  "DOOM{There's}",
  "DOOM{only}",
  "DOOM{one}",
  "DOOM{beer}",
  "DOOM{left}",
  "DOOM{doomsday_sequence_complete}"
];

export default function Home() {
  /* -----------------------------
       DOOM ASCII intro + history
     ------------------------------*/
  const [history, setHistory] = useState([
    "███╗   ███╗ █████╗ ███████╗██╗  ██╗",
    "████╗ ████║██╔══██╗██╔════╝██║ ██╔╝",
    "██╔████╔██║███████║███████╗█████╔╝ ",
    "██║╚██╔╝██║██╔══██║╚════██║██╔═██╗ ",
    "██║ ╚═╝ ██║██║  ██║███████║██║  ██╗",
    "╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝",
    "       MF DOOM // DOOMCORE",
    "",
    "OPERATION DOOMSDAY // GROUNDSTATION MF-01",
    "Link Status: [ESTABLISHED]",
    "",
    "Type `help` to list available commands."
  ]);

  /* -----------------------------
         INPUT + COMMAND STATE
     ------------------------------*/
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastHex, setLastHex] = useState(null);

  const backendBase =
    process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  /* -----------------------------
         COMMAND HISTORY (↑ / ↓)
     ------------------------------*/
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

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

  /* -----------------------------
           FLAG SYSTEM STATE
     ------------------------------*/
  const [flagInput, setFlagInput] = useState("");
  const [flagStatus, setFlagStatus] = useState("");
  const [foundFlags, setFoundFlags] = useState([]);
  const [doomsdayActive, setDoomsdayActive] = useState(false);
  const totalFlags = EXPECTED_FLAGS.length;

  const flagProgress = (foundFlags.length / totalFlags) * 100;

  const handleFlagSubmit = (e) => {
    e.preventDefault();
    const raw = flagInput.trim();
    if (!raw) return;

    const normalized = raw; // keep exact match for now
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

  // When all flags are found, activate DOOMSDAY
  useEffect(() => {
    if (!doomsdayActive && foundFlags.length === totalFlags) {
      setDoomsdayActive(true);
      pushLine("=== DOOMSDAY SEQUENCE COMPLETE ===");
      pushLine("DOOMSDAY LASER: TARGET LOCKED.");
      pushLine("EARTH: MASK OFF.");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [foundFlags, totalFlags, doomsdayActive]);

  /* -----------------------------
           LINE CHUNKING (NO TRUNCATION)
     ------------------------------*/
  const MAX_LINE_LEN = 44; // after this, we hard-wrap to a new line

  const chunkLine = (line) => {
    if (typeof line !== "string") return [];
    if (line.length <= MAX_LINE_LEN) return [line];
    const chunks = [];
    for (let i = 0; i < line.length; i += MAX_LINE_LEN) {
      chunks.push(line.slice(i, i + MAX_LINE_LEN));
    }
    return chunks;
  };

  /* -----------------------------
           SCREEN FLICKER EFFECT
     ------------------------------*/
  const flickerScreen = () => {
    if (typeof document === "undefined") return;
    const el = document.body;
    el.style.filter = "brightness(1.5) contrast(1.2)";
    setTimeout(() => {
      el.style.filter = "";
    }, 120);
  };

  const pushLine = (line) => {
    // accept only string; allow empty string for spacing
    if (typeof line !== "string") return;

    const chunks = chunkLine(line);
    flickerScreen();
    setHistory((h) => [...h, ...chunks]);
  };

  /* -----------------------------
             SAT ORBIT SYSTEM
     ------------------------------*/
  const [orbitInfo, setOrbitInfo] = useState({ lat: 0, lon: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      const t = Date.now() / 1000;
      const orbitalPeriod = 92 * 60; // 92-minute LEO orbit
      const phase = (t % orbitalPeriod) / orbitalPeriod;

      const lat = Math.sin(phase * 2 * Math.PI) * 45; // ±45°
      const lon = phase * 360 - 180; // -180..180

      setOrbitInfo({ lat, lon });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  /* -----------------------------
           RANDOM VILLAIN ALARMS
     ------------------------------*/
  useEffect(() => {
    const messages = [
      "[ALERT] Mask resonance spike detected on villain frequency.",
      "[WARN] DOOMCORE coolant levels dipping below villain threshold.",
      "[ALERT] Unauthorized hero comms intercepted. Scrambling mask.",
      "[WARN] Beam alignment jitter — suggest minor villain calibration.",
      "[INFO] Latent DOOM energy detected in lower orbit sectors."
    ];

    let active = true;
    const schedule = () => {
      const timeout = 45000 + Math.random() * 30000; // 45–75s
      setTimeout(() => {
        if (!active) return;
        const msg = messages[Math.floor(Math.random() * messages.length)];
        pushLine(msg);
        schedule();
      }, timeout);
    };
    schedule();

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* -----------------------------
           TYPEWRITER LINE OUTPUT
     ------------------------------*/
  function TypeLine({ text }) {
    // make sure text is always a string to avoid "undefined" glitches
    const safeText = typeof text === "string" ? text : "";
    const [shown, setShown] = useState("");

    useEffect(() => {
      setShown("");
      if (!safeText) return;
      let i = 0;
      const timer = setInterval(() => {
        setShown((s) => s + safeText[i]);
        i++;
        if (i >= safeText.length) clearInterval(timer);
      }, 8);
      return () => clearInterval(timer);
    }, [safeText]);

    return <div style={{ wordBreak: "break-all" }}>{shown}</div>;
  }

  /* -----------------------------
                   SEND CMD
     ------------------------------*/
  const handleSubmit = async (e) => {
    e.preventDefault();
    const line = input.trim();
    if (!line) return;

    if (line.toLowerCase() === "reboot") {
      flickerScreen();
      setHistory([
        "      ▄██████████████▄",
        "    ▄██████████████████▄",
        "   ███████▀▀▀▀▀▀▀▀███████",
        "   █████▀  DOOMCORE  ▀█████",
        "   ████▌ 🔥 REBOOT 🔥 ▐████",
        "   ████▌  MF DOOM     ▐████",
        "   █████▄            ▄█████",
        "    ██████▄▄▄▄▄▄▄▄▄▄██████",
        "      ▀████████████████▀",
        "",
        "DOOMCORE REBOOT SEQUENCE INITIATED...",
        ""
      ]);
    }

    pushLine(`> ${line}`);
    setInput("");

    setCommandHistory((h) => [...h, line]);
    setHistoryIndex(-1);

    if (busy) {
      pushLine("[WAIT] Command already running...");
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
          setLastHex(data.raw_hex);
        }
      }
    } catch (err) {
      pushLine(`[ERR] ${err.message || String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  /* -----------------------------
            QUICK BTN STYLE
     ------------------------------*/
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

  /* -----------------------------
                     UI
     ------------------------------*/
  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top, #441111 0, #050505 55%, #000000 100%)",
        color: "#f5f5f5",
        fontFamily:
          'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
        padding: "24px",
        position: "relative",
        overflow: "hidden"
      }}
    >
      {/* CRT Scanlines */}
      <div
        style={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(rgba(255,255,255,0.15) 1px, rgba(0,0,0,0) 1px)",
          backgroundSize: "100% 2px",
          mixBlendMode: "overlay",
          animation: "scan 18s linear infinite"
        }}
      ></div>

      {/* Global Animations */}
      <style jsx global>{`
        @keyframes scan {
          0% {
            transform: translateY(-100%);
          }
          100% {
            transform: translateY(100%);
          }
        }

        /* 
          🔥 SWEEP-BLINK (cursor fade)
          CRT-style cursor blink
        */
        .blink {
          animation: cursorBlink 2.8s ease-in-out infinite;
        }
        @keyframes cursorBlink {
          0% {
            opacity: 1;
          }
          45% {
            opacity: 1;
          }
          55% {
            opacity: 0;
          }
          65% {
            opacity: 1;
          }
          100% {
            opacity: 1;
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
          {/* ---------------- TERMINAL ---------------- */}
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
                alignItems: "center",
                background: doomsdayActive
                  ? "linear-gradient(90deg, rgba(255,0,0,0.7), rgba(80,0,0,0.8))"
                  : "linear-gradient(90deg, rgba(120,0,0,0.7), rgba(40,0,0,0.4))"
              }}
            >
              <span>
                DOOMCORE GROUNDSTATION CONSOLE
                {doomsdayActive && " // LASER: ARMED"}
              </span>
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
                whiteSpace: "pre-wrap",
                wordBreak: "break-all"
              }}
            >
              {history.map((line, idx) => (
                <TypeLine key={idx} text={line} />
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
              <span style={{ color: "#ff4444" }}>
                mf@doomcore:~$ <span className="blink">█</span>
              </span>
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
                placeholder="type 'help', 'dump 0 512', 'leak', 'fw_info', 'reboot'..."
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

          {/* ---------------- SIDEBAR ---------------- */}
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
            {/* ORBIT */}
            <div>
              <h2 style={{ fontSize: "1rem", marginBottom: 4 }}>
                DOOMSAT-1 LIVE ORBIT
              </h2>
              <div style={{ fontSize: "0.8rem", opacity: 0.8 }}>
                MASK ALIGNMENT: NOMINAL
              </div>
              <div style={{ marginTop: 8, fontSize: "0.8rem" }}>
                LAT: {orbitInfo.lat.toFixed(2)}°
              </div>
              <div style={{ fontSize: "0.8rem" }}>
                LON: {orbitInfo.lon.toFixed(2)}°
              </div>

              <div
                style={{
                  marginTop: 10,
                  height: 120,
                  borderRadius: 8,
                  border: "1px solid #333",
                  background:
                    "radial-gradient(circle at center, #220000 0, #050505 60%, #000000 100%)",
                  position: "relative",
                  overflow: "hidden",
                  fontSize: "0.65rem",
                  color: "#ccc"
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    inset: 8,
                    border: "1px dashed #552222",
                    borderRadius: 6
                  }}
                />

                <div
                  style={{
                    position: "absolute",
                    left: `${((orbitInfo.lon + 180) / 360) * 100}%`,
                    top: `${50 - (orbitInfo.lat / 90) * 40}%`,
                    transform: "translate(-50%, -50%)",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "#ff5555",
                    boxShadow: "0 0 10px #ff5555"
                  }}
                />

                <div style={{ position: "absolute", bottom: 4, left: 8 }}>
                  DOOMSAT-1
                </div>
                <div style={{ position: "absolute", bottom: 4, right: 8 }}>
                  TARGET ZONE
                </div>
              </div>
            </div>

            {/* DOOMSDAY LASER PROGRESS */}
            <div>
              <h3 style={{ fontSize: "0.9rem", marginBottom: 4 }}>
                DOOMSDAY LASER PROGRESS
              </h3>
              <div
                style={{
                  marginTop: 4,
                  height: 8,
                  borderRadius: 999,
                  background: "#220000",
                  overflow: "hidden"
                }}
              >
                <div
                  style={{
                    width: `${flagProgress}%`,
                    height: "100%",
                    background: doomsdayActive
                      ? "linear-gradient(90deg, #ffdd55, #ff0000)"
                      : "linear-gradient(90deg, #33ff88, #ffee33, #ff3333)",
                    transition: "width 0.4s"
                  }}
                ></div>
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  marginTop: 4,
                  opacity: 0.8
                }}
              >
                Flags found: {foundFlags.length} / {totalFlags}{" "}
                {doomsdayActive && " // DOOMSDAY LASER: ACTIVATED"}
              </div>
            </div>

            {/* FLAG INPUT */}
            <div>
              <h3 style={{ fontSize: "0.9rem", marginBottom: 4 }}>
                Submit Flag
              </h3>
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
                    fontSize: "0.8rem",
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
                    fontSize: "0.8rem",
                    cursor: "pointer",
                    color: "#f5f5f5",
                    textAlign: "center"
                  }}
                >
                  Check Flag
                </button>
              </form>
              {flagStatus && (
                <div
                  style={{
                    fontSize: "0.75rem",
                    marginTop: 4,
                    opacity: 0.9
                  }}
                >
                  {flagStatus}
                </div>
              )}
            </div>

            {/* QUICK ACTIONS */}
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

            {/* HEX PREVIEW */}
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
