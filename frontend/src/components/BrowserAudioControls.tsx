import { useEffect, useRef, useState } from "react";
import { useCallStore } from "../store/callStore";
import { AudioSource, CaptureHandle, CaptureState, startBrowserAudio } from "../lib/browserAudio";

function CaptureSource({ callId, source, consent, ended }: { callId: string; source: AudioSource; consent: boolean; ended: boolean }) {
  const capture = useRef<CaptureHandle | null>(null);
  const [state, setState] = useState<CaptureState>("idle");
  const [error, setError] = useState("");
  const [level, setLevel] = useState(0);
  const active = ["selecting", "connecting", "streaming"].includes(state);
  const tab = source === "tab";

  useEffect(() => () => { capture.current?.stop(); }, [callId]);
  useEffect(() => { if (!consent || ended) capture.current?.stop(); }, [consent, ended]);

  const start = () => {
    if (!consent || ended || active) return;
    capture.current?.stop();
    capture.current = startBrowserAudio({ callId, source, onState: setState, onLevel: setLevel, onError: setError });
  };
  return (
    <div className="flex flex-col gap-1 min-w-[220px]">
      <div className="flex items-center gap-2">
        <button onClick={active ? () => capture.current?.stop() : start}
          disabled={ended || (!consent && !active)}
          className={`px-3 py-2 rounded text-sm font-medium disabled:opacity-40 ${active ? "bg-danger text-white" : "bg-accent text-ink"}`}>
          {active ? `Stop ${tab ? "tab audio" : "microphone"}` : tab ? "Share Meet tab audio" : "Capture my microphone"}
        </button>
        {state === "streaming" && <meter aria-label={tab ? "Meeting audio level" : "Microphone audio level"}
          min={0} max={1} value={Math.min(1, level * 4)} className="w-20" />}
      </div>
      <span className="text-xs text-muted" role="status">
        {state === "selecting" ? "Choose a source in the browser permission dialog…"
          : state === "connecting" ? "Connecting audio…"
          : state === "streaming" ? `${tab ? "Meeting" : "Microphone"} audio streaming${level < 0.002 ? " — waiting for speech" : ""}`
          : tab ? "Other participants → client transcript" : "Optional: your voice → rep transcript"}
      </span>
      {error && <span role="alert" className="text-xs text-danger max-w-lg">{error}</span>}
    </div>
  );
}

export default function BrowserAudioControls() {
  const call = useCallStore((s) => s.call);
  const [consent, setConsent] = useState(false);
  useEffect(() => { setConsent(false); }, [call?.call_id]);
  if (!call || call.demo) return null;
  return (
    <section aria-label="Live meeting audio" className="flex flex-col gap-3">
      <label className="flex items-center gap-2 text-sm text-copy">
        <input type="checkbox" className="accent-accent w-4 h-4 shrink-0" checked={consent} disabled={call.ended} onChange={(event) => setConsent(event.target.checked)} />
        Everyone on the call consents to transcription.
      </label>
      <div className="flex flex-wrap gap-4">
        <CaptureSource key={`${call.call_id}-tab`} callId={call.call_id} source="tab" consent={consent} ended={call.ended} />
        <CaptureSource key={`${call.call_id}-mic`} callId={call.call_id} source="microphone" consent={consent} ended={call.ended} />
      </div>
      <p className="text-xs text-muted">Only audio is sent for transcription. Your tab video is not uploaded. Use headphones when capturing your microphone too.</p>
    </section>
  );
}
