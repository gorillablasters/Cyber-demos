import DoomHeader from "../components/DoomHeader";
import { useEffect, useState } from "react";

const API = "http://localhost:8000";

function hexToBytes(hex: string): Uint8Array {
  const clean = hex.trim();
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function parseOuterFrame(frameHex: string) {
  const b = hexToBytes(frameHex);
  if (b.length < 10) return null;
  if (!(b[0] === 0xd0 && b[1] === 0x0d)) return null;
  const satId = b[2];
  const ftype = b[3];
  const seq = b[4] | (b[5] << 8);
  const len = b[6] | (b[7] << 8);
  if (8 + len + 2 !== b.length) return { satId, ftype, seq, len, error: "LEN mismatch" };
  const payload = b.slice(8, 8 + len);
  return { satId, ftype, seq, len, payloadHex: Array.from(payload).map(b=>b.toString(16).padStart(2,'0')).join('') };
}

function parseDownlinkPayload(payloadHex: string) {
  const b = hexToBytes(payloadHex);
  if (b.length < 8) return null;
  if (!(b[0] === 0x44 && b[1] === 0x4c)) return null; // "DL"
  const ver = b[2];
  const satId = b[3];
  const tlvLen = b[4] | (b[5] << 8);
  if (6 + tlvLen + 2 !== b.length) return { ver, satId, tlvLen, error: "TLV LEN mismatch" };
  const tlvs = b.slice(6, 6 + tlvLen);

  const parsed: any[] = [];
  let i = 0;
  while (i + 2 <= tlvs.length) {
    const t = tlvs[i];
    const n = tlvs[i + 1];
    i += 2;
    if (i + n > tlvs.length) break;
    const v = tlvs.slice(i, i + n);
    i += n;
    parsed.push({ t, n, vHex: Array.from(v).map(b=>b.toString(16).padStart(2,'0')).join('') });
  }

  return { ver, satId, tlvLen, tlvs: parsed };
}

export default function DownlinkPage() {
  const [satId, setSatId] = useState<string>("");
  const [frames, setFrames] = useState<any[]>([]);
  const [auto, setAuto] = useState<boolean>(false);

  async function pull() {
    const body: any = { max_frames: 10 };
    if (satId.trim() !== "") body.sat_id = parseInt(satId, 0);
    const r = await fetch(`${API}/api/sim/downlink`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    const j = await r.json();
    const out: any[] = [];
    for (const fh of j.frames || []) {
      const outer = parseOuterFrame(fh);
      const inner = outer?.payloadHex ? parseDownlinkPayload(outer.payloadHex) : null;
      out.push({ frameHex: fh, outer, inner });
    }
    setFrames(out);
  }

  useEffect(() => {
    pull();
  }, []);

  useEffect(() => {
    if (!auto) return;
    const t = setInterval(pull, 1000);
    return () => clearInterval(t);
  }, [auto, satId]);

  return (
    <>
      <DoomHeader />
      <main style={{ padding: 16 }}>
        <h2>Downlink Frames</h2>
        <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
          <label>
            SAT_ID (optional):{" "}
            <input
              value={satId}
              onChange={(e) => setSatId(e.target.value)}
              placeholder="e.g. 0x02"
              style={{ width: 120 }}
            />
          </label>
          <button onClick={pull}>Pull</button>
          <label>
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> Auto
          </label>
        </div>

        {frames.length === 0 ? (
          <p>No frames popped.</p>
        ) : (
          frames.map((f, idx) => (
            <div
              key={idx}
              style={{
                border: "1px solid #333",
                borderRadius: 8,
                padding: 12,
                marginBottom: 12,
                background: "#0b0b0b",
              }}
            >
              <div style={{ marginBottom: 8 }}>
                <strong>Frame #{idx + 1}</strong>
                {f.outer ? (
                  <span style={{ marginLeft: 12 }}>
                    sat=0x{f.outer.satId.toString(16)} type=0x{f.outer.ftype.toString(16)} seq={f.outer.seq}
                  </span>
                ) : (
                  <span style={{ marginLeft: 12 }}>(unparsed)</span>
                )}
              </div>

              {f.inner ? (
                <>
                  <div style={{ marginBottom: 8 }}>
                    DLv{f.inner.ver} sat=0x{f.inner.satId.toString(16)} tlv_len={f.inner.tlvLen}
                    {f.inner.error ? <span style={{ marginLeft: 8, color: "tomato" }}>{f.inner.error}</span> : null}
                  </div>
                  <div style={{ fontFamily: "monospace", fontSize: 12 }}>
                    {f.inner.tlvs?.map((t: any, i: number) => (
                      <div key={i}>
                        TLV t=0x{t.t.toString(16).padStart(2, "0")} len={t.n} v={t.vHex}
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div style={{ color: "#aaa" }}>No DL packet decoded (see raw hex below).</div>
              )}

              <details style={{ marginTop: 10 }}>
                <summary>Raw frame hex</summary>
                <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{f.frameHex}</pre>
              </details>
            </div>
          ))
        )}
      </main>
    </>
  );
}
