import { useEffect } from "react";
import { useCallStore } from "../store/callStore";
import { eventsWs, api } from "./api";

export function useEvents(callId: string | null) {
  const applyEvent = useCallStore((s) => s.applyEvent);
  const setConnected = useCallStore((s) => s.setConnected);
  const setCall = useCallStore((s) => s.setCall);

  useEffect(() => {
    if (!callId) return;
    let ws: WebSocket | null = null;
    let closed = false;

    const connect = () => {
      ws = eventsWs(callId);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) setTimeout(connect, 1500); // reconnect + resync
      };
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        applyEvent(msg.type, msg.payload);
      };
    };
    connect();

    // initial resync
    api(`/calls/${callId}`).then((state) => { if (state.call_id) setCall(state); });

    return () => { closed = true; ws?.close(); };
  }, [callId]);
}
