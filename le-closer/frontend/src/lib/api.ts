const BASE = "http://localhost:8000";

export async function api(path: string, method = "GET", body?: any) {
  const resp = await fetch(BASE + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return resp.json();
}

export function eventsWs(callId: string) {
  return new WebSocket(`ws://localhost:8000/ws/events/${callId}`);
}
