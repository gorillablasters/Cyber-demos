import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "../styles/header.module.css";
import { apiGet, apiPost, getSid } from "../lib/api";

type SessionResponse = { ok: boolean; sid?: string };

export default function DoomHeader() {
  const [sid, setSid] = useState<string>(() => (typeof window === "undefined" ? "" : getSid()));

  const [copied, setCopied] = useState<boolean>(false);
  const [commandCopied, setCommandCopied] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [resetOk, setResetOk] = useState<boolean>(false);
  const [resetErr, setResetErr] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await apiGet<SessionResponse>("/api/sim/session");

        if (!cancelled && data?.ok && data.sid && data.sid !== getSid()) {
          localStorage.setItem("doom_sid", data.sid);
          setSid(data.sid);
        }
      } catch {
        // Non-fatal; still display localStorage SID
      }
    }

    if (typeof window !== "undefined") setSid(getSid());

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function copyExportCommand() {
    if (!sid) return;
    try {
      await navigator.clipboard.writeText(`export DOOMGS_SID=${sid}`);
      setCommandCopied(true);
      window.setTimeout(() => setCommandCopied(false), 900);
    } catch {
      // ignore
    }
  }

  async function copySid() {
    if (!sid) return;
    try {
      await navigator.clipboard.writeText(sid);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 900);
    } catch {
      // ignore
    }
  }

  async function resetSession() {
    if (!sid || resetting) return;

    if (typeof window !== "undefined") {
      const ok = window.confirm("Reset your session world state? This cannot be undone.");
      if (!ok) return;
    }

    setResetting(true);
    setResetErr("");
    setResetOk(false);

    try {
      const data = await apiPost<any>("/api/sim/reset");

      if (!data?.ok) {
        throw new Error(data?.error || "reset failed");
      }

      setResetOk(true);
      window.setTimeout(() => window.location.reload(), 250);
    } catch (e: any) {
      setResetErr(String(e?.message || e));
    } finally {
      setResetting(false);
    }
  }

  return (
    <header className={styles.header}>
      <div className={styles.title}>MF DOOM — ORBITAL OPS CONSOLE</div>

      <nav className={styles.nav}>
        <Link href="/">Dashboard</Link>
        <Link href="/telemetry">Telemetry</Link>
        <Link href="/rf">RF</Link>
        <Link href="/crosslink">Crosslink</Link>
        <Link href="/firmware">Firmware</Link>
        <Link href="/downlink">Downlink</Link>
        <Link href="/hex">Hex</Link>
      </nav>

      <div style={{ marginLeft: "auto", display: "flex", flexDirection: "column", gap: "6px", alignItems: "flex-end" }}>
        <div style={{ fontSize: 12, opacity: 0.9, textAlign: "right" }}>
          <div>
            <span style={{ opacity: 0.8 }}>Session SID</span>
          </div>
          <div style={{ fontFamily: "monospace", wordBreak: "break-all", maxWidth: 420 }}>
            {sid ? sid : "(loading)"}
          </div>
          <div style={{ fontFamily: "monospace", opacity: 0.8, marginTop: 2 }}>
            {sid ? `export DOOMGS_SID=${sid}` : ""}
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={copyExportCommand}
            disabled={!sid}
            style={{
              fontSize: 12,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.25)",
              background: "transparent",
              color: "inherit",
              cursor: sid ? "pointer" : "not-allowed",
            }}
            title="Copy Export Command"
          >
            {commandCopied ? "Copied" : "Copy Export Command"}
          </button>

          <button
            onClick={copySid}
            disabled={!sid}
            style={{
              fontSize: 12,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.25)",
              background: "transparent",
              color: "inherit",
              cursor: sid ? "pointer" : "not-allowed",
            }}
            title="Copy SID"
          >
            {copied ? "Copied" : "Copy SID"}
          </button>

          <button
            onClick={resetSession}
            disabled={!sid || resetting}
            style={{
              fontSize: 12,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.25)",
              background: "rgba(255,255,255,0.06)",
              color: "inherit",
              cursor: !sid || resetting ? "not-allowed" : "pointer",
            }}
            title="Reset this session's world state"
          >
            {resetting ? "Resetting…" : resetOk ? "Reset ✓" : "Reset"}
          </button>
        </div>

        {resetErr ? (
          <div style={{ fontSize: 12, opacity: 0.85, color: "#ffcc66", maxWidth: 420, textAlign: "right" }}>
            {resetErr}
          </div>
        ) : null}
      </div>
    </header>
  );
}
