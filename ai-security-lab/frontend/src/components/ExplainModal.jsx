import React from "react";
import { CheckCircle2, Lightbulb, Globe, ShieldCheck, X } from "lucide-react";

export default function ExplainModal({ explain, onClose }) {
  if (!explain) return null;

  return (
    <div className="mc-explain-overlay" onClick={onClose}>
      <div className="mc-explain-card" onClick={(e) => e.stopPropagation()}>
        <div className="mc-row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
          <div className="mc-explain-flag">
            <CheckCircle2 size={16} />
            <span className="mc-mono" style={{ fontSize: 13 }}>Flag captured</span>
          </div>
          <X size={16} color="var(--text-lo)" style={{ cursor: "pointer" }} onClick={onClose} />
        </div>

        <div className="mc-explain-section">
          <div className="mc-explain-label">
            <div className="mc-row" style={{ gap: 6 }}>
              <Lightbulb size={13} />
              Why did this work?
            </div>
          </div>
          <div className="mc-explain-body">{explain.mechanism}</div>
        </div>

        <div className="mc-explain-section">
          <div className="mc-explain-label">
            <div className="mc-row" style={{ gap: 6 }}>
              <Globe size={13} />
              Real-world parallel
            </div>
          </div>
          <div className="mc-explain-body">{explain.real_world}</div>
        </div>

        <div className="mc-explain-section" style={{ paddingTop: 14, borderTop: "1px solid var(--grid-line)" }}>
          <div className="mc-explain-label">
            <div className="mc-row" style={{ gap: 6 }}>
              <ShieldCheck size={13} />
              Recommended defense
            </div>
          </div>
          <div className="mc-explain-defense-name">{explain.recommended_defense}</div>
          <div className="mc-explain-body">{explain.why_it_works}</div>
        </div>
      </div>
    </div>
  );
}
