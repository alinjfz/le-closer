import { MessageSquareText, Search, ListChecks, Volume2, VolumeX, Loader2 } from "lucide-react";
import { useCallStore } from "../../store/callStore";
import { useCopilotSpeech } from "../../lib/useCopilotSpeech";
import RichText from "../RichText";
import LiveCard from "./LiveCard";

export default function CardsPanel() {
  const call = useCallStore((s) => s.call);
  const voice = useCopilotSpeech();
  const answers = call?.assistant_answers || [];
  const latestActivity = [...(call?.activity || [])].reverse().find(entry => entry.agent === "Copilot");
  const answering = !call?.ended && latestActivity?.status === "working";
  const cards = call?.cards ?? [];
  const active = cards.filter((c) => c.status === "active" || c.status === "pinned");
  const history = cards.filter((c) => c.status === "history" || c.status === "dismissed");
  return (
    <div className="workspace-panel copilot-panel">
      <div className="panel-heading"><div className="flex items-center gap-2"><h2>Live copilot</h2><button type="button" className="tool-icon-button" aria-label={voice.enabled ? "Mute copilot" : "Unmute copilot"} aria-pressed={!voice.enabled} title={voice.enabled ? "Mute spoken answers" : "Unmute spoken answers"} disabled={voice.pending || !call || call.ended} onClick={() => void voice.toggleMute()}>{voice.pending ? <Loader2 size={17} className="animate-spin" /> : voice.enabled ? <Volume2 size={17} /> : <VolumeX size={17} />}</button></div><span className="text-xs text-muted">{active.length} suggestions</span></div>
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-3">
        {voice.error && <p role="alert" className="text-danger text-sm">{voice.error}</p>}
        {latestActivity?.status === "error" && <p role="alert" className="text-danger text-sm">{latestActivity.message}</p>}
        {answering && <div role="status" className="copilot-answer-card"><Loader2 size={18} className="animate-spin" /> Copilot is preparing an answer…</div>}
        {[...answers].reverse().map((answer, index) => <article key={answer.id} className="copilot-answer-card" aria-label="Copilot answer">
          <div className="flex items-center gap-2 text-accent"><h3 className="font-medium">Copilot answer</h3></div>
          <p className="text-muted text-sm mt-2">{answer.question}</p>
          <div className="mt-3" aria-live={index === 0 ? "polite" : "off"}><RichText text={answer.text} collapsible /></div>
          {index === 0 && voice.audioUrl && voice.enabled && !call?.ended && <audio ref={voice.audioRef} src={voice.audioUrl} controls aria-label="Spoken copilot answer" className="mt-3 w-full" />}
        </article>)}
        {active.length === 0 && answers.length === 0 && !answering && <div className="copilot-empty">

          <h3>{call?.ended ? "No suggestions from this call" : "Room to focus on the conversation"}</h3>
          <p>{call?.ended ? "Suggestions generated during your call will remain here for review." : call?.demo ? "Press Start in the navigation bar. Suggestions will appear as the conversation unfolds." : "Once you share audio, your copilot will bring useful answers and suggestions here."}</p>
          <div className="copilot-capabilities"><span><MessageSquareText size={17} /> Questions & objection support</span><span><Search size={17} /> Research & integration checks</span><span><ListChecks size={17} /> Promises & next steps</span></div>
        </div>}
        {active.map((c) => <LiveCard key={c.id} card={c} />)}
      </div>
      {history.length > 0 && <details className="border-t border-line p-4 text-sm text-muted"><summary className="cursor-pointer">Previous suggestions ({history.length})</summary><div className="mt-3 space-y-2 max-h-32 overflow-y-auto">{history.map((c) => <p key={c.id}>{c.title}</p>)}</div></details>}
    </div>
  );
}
