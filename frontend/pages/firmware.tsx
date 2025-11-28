
import React, { useState } from "react";

export default function FirmwarePage() {
  const [file, setFile] = useState(null);
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const backendBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const push = (line: string) => setLog((l) => [...l, line]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      push("[ERR] choose a firmware file first");
      return;
    }
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${backendBase}/api/upload_firmware`, {
        method: "POST",
        body: form
      });
      const data = await res.json();
      if (!data.ok) {
        push("[ERR] upload failed");
      } else {
        push("=== RESPONSE TEXT ===");
        if (data.text) {
          for (const line of data.text.split(/\r?\n/)) {
            push(line);
          }
        }
      }
    } catch (err: any) {
      push(`[ERR] ${err.message || String(err)}`);
    } finally {
      setBusy(false);
    }
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
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <h1 style={{ fontSize: "1.6rem", marginBottom: 8 }}>
          DOOMCORE Firmware Uplink
        </h1>
        <p style={{ fontSize: "0.9rem", opacity: 0.85, marginBottom: 16 }}>
          Upload a crafted firmware image. Only the first 4 bytes of the
          signature are validated (hint: MFDO...). A successful patch may alter
          DOOMSAT boot behavior and reveal flags.
        </p>

        <form onSubmit={handleSubmit} style={{ marginBottom: 16 }}>
          <input
            type="file"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                // @ts-ignore
                setFile(e.target.files[0]);
              }
            }}
            style={{ marginBottom: 8 }}
          />
          <div>
            <button
              type="submit"
              disabled={busy}
              style={{
                background: busy ? "#552222" : "#aa2222",
                border: "none",
                borderRadius: 6,
                padding: "6px 12px",
                fontSize: "0.9rem",
                cursor: busy ? "not-allowed" : "pointer",
                color: "#f5f5f5"
              }}
            >
              {busy ? "Uploading..." : "Upload Firmware"}
            </button>
          </div>
        </form>

        <div
          style={{
            background: "#080808",
            borderRadius: 10,
            border: "1px solid #552222",
            padding: 12,
            minHeight: 200,
            fontSize: "0.8rem",
            whiteSpace: "pre-wrap"
          }}
        >
          {log.map((line, idx) => (
            <div key={idx}>{line}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
