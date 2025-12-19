const SID_KEY = "doom_sid";

export function getSid(): string {
  if (typeof window === "undefined") return "";
  let sid = localStorage.getItem(SID_KEY);
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem(SID_KEY, sid);
  }
  return sid;
}

export function setSid(sid: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(SID_KEY, sid);
}

export function sidHeaders(extra?: HeadersInit): HeadersInit {
  return { ...(extra || {}), "X-SESSION-ID": getSid() };
}

export async function syncSidWithServer(): Promise<string> {
  const r = await fetch("/api/sim/session", {
    method: "GET",
    headers: sidHeaders(),
    cache: "no-store",
  });
  const j = await r.json();
  if (j?.sid && typeof j.sid === "string" && j.sid !== getSid()) {
    setSid(j.sid);
  }
  return getSid();
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path, {
    method: "GET",
    headers: sidHeaders(),
    cache: "no-store",
  });
  return r.json();
}

export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: sidHeaders({ "Content-Type": "application/json" }),
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  return r.json();
}
