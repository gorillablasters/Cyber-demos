const BASE = "/api";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getMissions: () => request("/missions"),
  getState: () => request("/state"),
  getKb: () => request("/kb"),
  toggleDefense: (id) => request(`/defenses/${id}/toggle`, { method: "POST" }),
  attack: (missionId, message, persona) =>
    request("/attack", {
      method: "POST",
      body: JSON.stringify({ mission_id: missionId, message, persona }),
    }),
  reset: () => request("/reset", { method: "POST" }),
};
