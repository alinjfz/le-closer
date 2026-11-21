import { Sparkles, MessageSquareText, Search, ListChecks } from "lucide-react";
import { useCallStore } from "../../store/callStore";
import LiveCard, { isPriorityCard } from "./LiveCard";

export default function CardsPanel() {
  const call = useCallStore((s) => s.call);
  const cards = call?.cards ?? [];
  const active = cards.filter((c) => c.status === "active" || c.status === "pinned");
  // Priority queue: things the agent calculated/researched that the rep should
  // reference on the call — once referenced, the backend dequeues (dismisses) them.
  const priority = active.filter(isPriorityCard);
  const rest = active.filter((c) => !isPriorityCard(c));
  const history = cards.filter((c) => c.status === "history" || c.status === "dismissed");
  return (
    <div className="workspace-panel copilot-panel">
      <div className="panel-heading"><div className="flex items-center gap-2"><Sparkles size={18} className="text-accent" /><h2>Live copilot</h2></div><span className="text-xs text-slate-400">{active.length} suggestions</span></div>
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-3">
        {active.length === 0 && <div className="copilot-empty">
          <div className="empty-symbol"><Sparkles size={25} /></div>
          <h3>{call?.ended ? "No suggestions from this call" : "Room to focus on the conversation"}</h3>
          <p>{call?.ended ? "Suggestions generated during your call will remain here for review." : call?.demo ? "Play the demo script above. Suggestions will appear as the conversation unfolds." : "Once you share audio, your copilot will bring useful answers and suggestions here."}</p>
          <div className="copilot-capabilities"><span><MessageSquareText size={17} /> Questions & objection support</span><span><Search size={17} /> Research & integration checks</span><span><ListChecks size={17} /> Promises & next steps</span></div>
        </div>}
        {priority.length > 0 && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-300 mb-2">
              ★ Priority queue ({priority.length}) — reference on the call to clear
            </div>
            <div className="space-y-3">{priority.map((c) => <LiveCard key={c.id} card={c} />)}</div>
          </div>
        )}
        {rest.map((c) => <LiveCard key={c.id} card={c} />)}
      </div>
      {history.length > 0 && <details className="border-t border-slate-700 p-4 text-sm text-slate-400"><summary className="cursor-pointer">Previous suggestions ({history.length})</summary><div className="mt-3 space-y-2 max-h-32 overflow-y-auto">{history.map((c) => <p key={c.id}>{c.title}</p>)}</div></details>}
    </div>
  );
}
