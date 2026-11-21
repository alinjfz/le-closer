import { useEffect, useRef, useState } from "react";
import { useCallStore } from "../store/callStore";
import { api } from "./api";

export function useCopilotSpeech() {
  const call = useCallStore(s => s.call);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const seen = useRef(new Set<string>());
  const enabled = call?.settings?.tts_enabled ?? true;
  const answers = call?.assistant_answers || [];
  const latest = answers[answers.length - 1];
  const callId = call?.call_id;

  useEffect(() => {
    seen.current = new Set(useCallStore.getState().call?.assistant_answers?.map(a => a.id) || []);
  }, [callId]);

  useEffect(() => {
    audioRef.current?.pause();
    setAudioUrl("");
    // Muted answers remain visible, but must not play later when unmuted.
    if (!latest || seen.current.has(latest.id)) return;
    seen.current.add(latest.id);
    if (!enabled || pending || call?.ended) return;
    const controller = new AbortController();
    let url: string | undefined;
    setError("");
    void (async () => {
      try {
        const response = await fetch(`/calls/${callId}/assistant/speech/${latest.id}`, { signal: controller.signal });
        if (!response.ok) throw new Error("Spoken answer unavailable. Check your Mistral speech access.");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setAudioUrl(url);
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Could not play speech.");
      }
    })();
    return () => {
      controller.abort();
      audioRef.current?.pause();
      if (url) URL.revokeObjectURL(url);
    };
  }, [latest?.id, enabled, pending, callId, call?.ended]);

  useEffect(() => {
    const player = audioRef.current;
    if (audioUrl && enabled && !pending && !call?.ended) void player?.play().catch(() => setError("Press play on the answer to hear it."));
    return () => player?.pause();
  }, [audioUrl, enabled, pending, call?.ended]);

  const toggleMute = async () => {
    if (!call) return;
    setPending(true); setError("");
    audioRef.current?.pause();
    setAudioUrl("");
    const result = await api(`/calls/${call.call_id}/assistant/settings`, "POST", { tts_enabled: !enabled });
    if (result.error) setError(result.error);
    else useCallStore.getState().applyEvent("assistant.settings", result.settings);
    setPending(false);
  };
  return { enabled, pending, error, toggleMute, audioRef, audioUrl };
}
