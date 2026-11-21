// Same-origin URLs: works both in the Docker image (FastAPI serves the built
// frontend on :8003) and in dev (vite proxies /calls, /ws, /health to :8003).
const BASE = "";

export async function api(path: string, method = "GET", body?: any) {
  const resp = await fetch(BASE + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return resp.json();
}

export function eventsWs(callId: string) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${window.location.host}/ws/events/${callId}`);
}
