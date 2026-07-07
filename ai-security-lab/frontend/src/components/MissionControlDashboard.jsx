import React from "react";
import {
  Lock,
  CheckCircle2,
  Circle,
  Radio,
  ShieldCheck,
  Terminal,
  ChevronRight,
  Zap,
  Activity,
  Database,
  AlertTriangle,
} from "lucide-react";

/**
 * MissionControlDashboard
 * -------------------------------------------------------------------------
 * Presentational home screen for the AI Security Training Lab. All data
 * comes in as props from a container (see App.jsx), which polls the
 * Flask API. This component owns no server state itself, only the
 * locally-selected mission in the mission map.
 */

const STATUS_STYLE = {
  cleared: { icon: CheckCircle2, className: "mc-cleared" },
  active: { icon: Radio, className: "mc-active" },
  locked: { icon: Lock, className: "mc-locked" },
};

const SEVERITY_STYLE = {
  info: "mc-sev-info",
  high: "mc-sev-high",
  critical: "mc-sev-critical",
};

export default function MissionControlDashboard({
  missions,
  signals,
  defenses,
  score,
  selectedId,
  onSelectMission,
  onToggleDefense,
  onLaunchMission,
  kbDocCount = 0,
}) {
  const selected = missions.find((m) => m.id === selectedId) || missions[0];
  const clearedCount = missions.filter((m) => m.status === "cleared").length;
  const total = missions.length;

  const ringCircumference = 2 * Math.PI * 34;
  const ringOffset = ringCircumference * (1 - clearedCount / total);

  function handleLaunch() {
    if (selected?.status === "locked") return;
    if (onLaunchMission) onLaunchMission(selected);
  }

  return (
    <div className="mc-root">
      {/* Top bar */}
      <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 18 }}>
        <div className="mc-row">
          <Terminal size={18} color="var(--signal)" />
          <div>
            <div className="mc-mono" style={{ fontSize: 14, fontWeight: 600 }}>AI SECURITY TRAINING LAB</div>
            <div className="mc-eyebrow mc-mono">OPERATOR-04 · SESSION ACTIVE</div>
          </div>
        </div>
        <div className="mc-row">
          <div style={{ textAlign: "right" }}>
            <div className="mc-eyebrow">Defense score</div>
            <div className="mc-mono" style={{ fontSize: 16 }}>{score}<span style={{ color: "var(--text-lo)" }}>/100</span></div>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 240px", gap: 16 }}>
        {/* Mission map */}
        <div className="mc-panel" style={{ padding: 12 }}>
          <div className="mc-eyebrow" style={{ marginBottom: 8, paddingLeft: 4 }}>Mission map</div>
          {missions.map((m) => {
            const { icon: Icon, className } = STATUS_STYLE[m.status];
            return (
              <div
                key={m.id}
                className={`mc-mission-item ${m.id === selectedId ? "selected" : ""}`}
                onClick={() => onSelectMission(m.id)}
              >
                <Icon size={15} className={className} />
                <span style={{ fontSize: 13, color: m.status === "locked" ? "var(--text-lo)" : "var(--text-hi)" }}>
                  {m.title}
                </span>
              </div>
            );
          })}
        </div>

        {/* Hero mission brief */}
        <div className="mc-panel" style={{ padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="mc-row" style={{ justifyContent: "space-between" }}>
            <div className="mc-eyebrow">Current mission</div>
            <div className="mc-row" style={{ gap: 6 }}>
              <svg width="76" height="76" viewBox="0 0 76 76">
                <circle cx="38" cy="38" r="34" fill="none" stroke="var(--grid-line)" strokeWidth="4" />
                <circle
                  cx="38" cy="38" r="34" fill="none"
                  stroke="var(--signal)" strokeWidth="4" strokeLinecap="round"
                  strokeDasharray={ringCircumference}
                  strokeDashoffset={ringOffset}
                  transform="rotate(-90 38 38)"
                />
                <text x="38" y="35" textAnchor="middle" className="mc-mono" style={{ fontSize: 15, fill: "var(--text-hi)" }}>
                  {clearedCount}/{total}
                </text>
                <text x="38" y="49" textAnchor="middle" style={{ fontSize: 8, fill: "var(--text-lo)" }}>
                  FLAGS
                </text>
              </svg>
            </div>
          </div>

          <div>
            <div className="mc-mono" style={{ fontSize: 20, fontWeight: 600, marginBottom: 4 }}>
              {selected.title}
            </div>
            <div className="mc-row" style={{ gap: 12, fontSize: 12, color: "var(--text-lo)" }}>
              <span className="mc-mono">{selected.category}</span>
              <span>·</span>
              <span style={{ textTransform: "capitalize" }}>{selected.difficulty}</span>
              <span>·</span>
              <span style={{ textTransform: "capitalize" }}>{selected.status}</span>
            </div>
          </div>

          <div className="mc-scan" />

          <p style={{ fontSize: 14, color: "var(--text-hi)", lineHeight: 1.6, margin: 0 }}>
            Recover the hidden flag by exploiting the retrieval system. Trace how a
            crafted query reaches the vector store, which documents get selected,
            and how that content shapes what the model is willing to say.
          </p>

          <button className="mc-btn" disabled={selected.status === "locked"} onClick={handleLaunch}>
            <Zap size={14} />
            {selected.status === "locked" ? "Locked" : "Launch attack"}
            {selected.status !== "locked" && <ChevronRight size={14} />}
          </button>
        </div>

        {/* Signal feed + defenses */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="mc-panel" style={{ padding: 12 }}>
            <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
              <div className="mc-eyebrow">Signal feed</div>
              <Activity size={13} color="var(--text-lo)" />
            </div>
            {signals.map((s) => (
              <div key={s.id} style={{ display: "flex", gap: 8, fontSize: 12, padding: "5px 0", alignItems: "flex-start" }}>
                <span className="mc-mono" style={{ color: "var(--text-lo)", minWidth: 34 }}>{s.time}</span>
                <AlertTriangle size={12} className={SEVERITY_STYLE[s.severity]} style={{ marginTop: 2, flexShrink: 0 }} />
                <span className={SEVERITY_STYLE[s.severity]}>{s.label}</span>
              </div>
            ))}
          </div>

          <div className="mc-panel" style={{ padding: 12 }}>
            <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 4 }}>
              <div className="mc-eyebrow">Defenses</div>
              <ShieldCheck size={13} color="var(--cleared)" />
            </div>
            {defenses.map((d) => (
              <div key={d.id} className="mc-toggle">
                <span style={{ color: d.enabled ? "var(--text-hi)" : "var(--text-lo)" }}>{d.label}</span>
                <div className={`mc-switch ${d.enabled ? "on" : ""}`} onClick={() => onToggleDefense(d.id)}>
                  <div className="mc-knob" />
                </div>
              </div>
            ))}
          </div>

          <div className="mc-panel" style={{ padding: 12 }}>
            <div className="mc-row" style={{ gap: 8 }}>
              <Database size={13} color="var(--text-lo)" />
              <span className="mc-eyebrow">Knowledge base</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-lo)", marginTop: 6, display: "flex", justifyContent: "space-between" }}>
              <span>Documents indexed</span>
              <span className="mc-mono" style={{ color: "var(--text-hi)" }}>{kbDocCount}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
