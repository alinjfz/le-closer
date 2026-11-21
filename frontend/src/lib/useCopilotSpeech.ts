import { useEffect, useRef, useState } from "react";
import { useCallStore } from "../store/callStore";
import { api } from "./api";
import { CopilotPlayback } from "./copilotPlayback";

export function useCopilotSpeech() {
  const call = useCallStore(s => s.call);
  const connected = useCallStore(s => s.connected);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [waitingForSilence, setWaitingForSilence] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const playback = useRef<CopilotPlayback | null>(null);
  const seen = useRef(new Set<string>());
  const enabled = call?.settings?.tts_enabled ?? true;
  const answers = call?.assistant_answers || [];
  const latest = answers[answers.length - 1];
  const callId = call?.call_id;

  useEffect(() => {
    seen.current = new Set(useCallStore.getState().call?.assistant_answers?.map(a => a.id) || []);
    const gate = new CopilotPlayback({
      onWaiting: setWaitingForSilence,
      onBlocked: () => setError("Press play on the answer to hear it."),
    });
    playback.current = gate;
    gate.transcriptActivity(useCallStore.getState().lastTranscriptActivityAt);
    const unsubscribe = useCallStore.subscribe((state, previous) => {
      if (state.call?.call_id !== callId) { gate.setActive(false); return; }
      if (state.lastTranscriptActivityAt !== previous.lastTranscriptActivityAt) {
        gate.transcriptActivity(state.lastTranscriptActivityAt);
      }
      // Stop immediately on mute, end, disconnect or navigation, rather than
      // waiting for a React render to clean up a pending timer or playing audio.
      if (!state.connected || !state.call || state.call.ended || !state.call.settings?.tts_enabled) gate.setActive(false);
    });
    return () => { unsubscribe(); gate.dispose(); if (playback.current === gate) playback.current = null; };
  }, [callId]);

  useEffect(() => {
    const controller = new AbortController();
    playback.current?.detach();
    setAudioUrl("");
    if (!latest || seen.current.has(latest.id)) return;
    seen.current.add(latest.id);
    if (!enabled || pending || call?.ended) return;
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
      playback.current?.detach();
      if (url) URL.revokeObjectURL(url);
    };
  }, [latest?.id, enabled, pending, callId, call?.ended]);

  useEffect(() => {
    const gate = playback.current;
    gate?.setActive(enabled && connected && !pending && !call?.ended);
    const player = audioRef.current;
    if (audioUrl && player && enabled && connected && !pending && !call?.ended) {
      gate?.attach(player, useCallStore.getState().lastTranscriptActivityAt);
    }
    return () => gate?.detach();
  }, [audioUrl, enabled, connected, pending, call?.ended, callId]);

  const toggleMute = async () => {
    if (!call) return;
    playback.current?.setActive(false);
    setPending(true); setError(""); setAudioUrl("");
    const result = await api(`/calls/${call.call_id}/assistant/settings`, "POST", { tts_enabled: !enabled });
    if (result.error) setError(result.error);
    else useCallStore.getState().applyEvent("assistant.settings", result.settings);
    setPending(false);
  };
  return {
    enabled, pending, error, toggleMute, audioRef, audioUrl, waitingForSilence,
    onPlay: (player: HTMLAudioElement) => { setError(""); playback.current?.onPlay(player); },
    onPause: (player: HTMLAudioElement) => playback.current?.onPause(player),
    onEnded: (player: HTMLAudioElement) => playback.current?.onEnded(player),
  };
}
