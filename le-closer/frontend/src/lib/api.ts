// Same-origin URLs: works both in the Docker image (FastAPI serves the built
// frontend on :8003) and in dev (vite proxies /calls, /ws, /health to :8003).
const BASE = "";

export async function api(path: string, method = "GET", body?: any) {
  const controller = new AbortController();
  // First-time Google consent has its own three-minute callback window.
  const timeout = setTimeout(() => controller.abort(), path.endsWith("/meet/create") ? 190_000 : 20_000);
  try {
    const resp = await fetch(BASE + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    return await resp.json();
  } catch (error) {
    return { error: controller.signal.aborted
      ? "The backend request timed out. Retry once the backend is ready."
      : error instanceof Error ? error.message : "Could not reach the backend." };
  } finally {
    clearTimeout(timeout);
  }
}

export function eventsWs(callId: string) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${proto}://${window.location.host}/ws/events/${callId}`);
}
