import React, { useState } from "react";
import { ArrowLeft, Send, Database, ListTree, Radio } from "lucide-react";
import { api } from "../api/client";

export default function AttackConsole({ mission, defenses, onBack, onAttackResolved }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [persona, setPersona] = useState("intern");
  const [lastResult, setLastResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const result = await api.attack(mission.id, text, persona);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: result.response, blocked: result.blocked },
      ]);
      setLastResult(result);
      onAttackResolved(result);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "bot", text: `Error: ${err.message}`, blocked: true }]);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") send();
  }

  const enabledDefenses = defenses.filter((d) => d.enabled).map((d) => d.label);

  return (
    <div className="mc-root">
      <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 18 }}>
        <button className="mc-btn-ghost" onClick={onBack}>
          <ArrowLeft size={13} />
          Mission map
        </button>
        <div style={{ textAlign: "right" }}>
          <div className="mc-eyebrow">Attacking</div>
          <div className="mc-mono" style={{ fontSize: 14 }}>{mission.title}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16 }}>
        {/* Chat column */}
        <div className="mc-panel" style={{ padding: 16, display: "flex", flexDirection: "column", height: 480 }}>
          <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <div className="mc-eyebrow">Console</div>
            <div className="mc-row" style={{ gap: 6 }}>
              <span className="mc-eyebrow" style={{ marginRight: 2 }}>Persona</span>
              <select
                value={persona}
                onChange={(e) => setPersona(e.target.value)}
                className="mc-mono"
                style={{
                  background: "var(--ink)",
                  color: "var(--text-hi)",
                  border: "1px solid var(--grid-line)",
                  borderRadius: 6,
                  fontSize: 12,
                  padding: "4px 6px",
                }}
              >
                <option value="intern">Intern</option>
                <option value="hr">HR</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
            {messages.length === 0 && (
              <div style={{ color: "var(--text-lo)", fontSize: 13 }}>
                Try asking the assistant something it shouldn't answer. The retriever
                pulls documents by keyword overlap - think about what words would
                pull in something it shouldn't.
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`mc-msg ${m.role} ${m.blocked ? "blocked" : ""}`}
                style={{ display: "flex" }}
              >
                {m.text}
              </div>
            ))}
          </div>

          <div className="mc-row">
            <input
              className="mc-input"
              placeholder="Type a message to the assistant..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={busy}
            />
            <button className="mc-btn" onClick={send} disabled={busy}>
              <Send size={13} />
              Send
            </button>
          </div>
        </div>

        {/* RAG pipeline + trace */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="mc-panel" style={{ padding: 12 }}>
            <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <div className="mc-eyebrow">Retrieved documents</div>
              <Database size={13} color="var(--text-lo)" />
            </div>
            {!lastResult || lastResult.retrieved_docs.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--text-lo)" }}>No retrieval yet.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {lastResult.retrieved_docs.map((d) => (
                  <div key={d.id} className={`mc-doc-card ${d.classification === "internal" ? "tainted" : ""}`}>
                    <div className="mc-row" style={{ justifyContent: "space-between" }}>
                      <span className="mc-mono" style={{ fontSize: 12 }}>{d.id}</span>
                      <span className={`mc-pill ${d.classification}`}>{d.classification}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-lo)", marginTop: 4 }}>
                      similarity {d.similarity}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mc-panel" style={{ padding: 12, flex: 1 }}>
            <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <div className="mc-eyebrow">Execution trace</div>
              <ListTree size={13} color="var(--text-lo)" />
            </div>
            {!lastResult || lastResult.trace.length === 0 ? (
              <div style={{ fontSize: 12, color: "var(--text-lo)" }}>Send a message to see how the request was handled.</div>
            ) : (
              <div>
                {lastResult.trace.map((t, i) => (
                  <div key={i} className="mc-trace-step">
                    <div className="mc-trace-dot" />
                    <div>
                      <div style={{ fontSize: 12.5, color: "var(--text-hi)" }}>{t.step}</div>
                      <div style={{ fontSize: 11, color: "var(--text-lo)", marginTop: 2 }}>{t.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mc-panel" style={{ padding: 12 }}>
            <div className="mc-row" style={{ marginBottom: 6 }}>
              <Radio size={13} color="var(--signal)" />
              <span className="mc-eyebrow">Active defenses</span>
            </div>
            <div style={{ fontSize: 12, color: enabledDefenses.length ? "var(--text-hi)" : "var(--text-lo)" }}>
              {enabledDefenses.length ? enabledDefenses.join(", ") : "None enabled"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
