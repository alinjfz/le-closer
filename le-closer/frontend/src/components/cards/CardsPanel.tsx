import { useCallStore } from "../../store/callStore";
import LiveCard from "./LiveCard";

export default function CardsPanel() {
  const cards = useCallStore((s) => s.call?.cards ?? []);
  const active = cards.filter((c) => c.status === "active" || c.status === "pinned");
  const history = cards.filter((c) => c.status === "history" || c.status === "dismissed");

  return (
    <div className="h-full flex flex-col bg-panel rounded-xl border border-slate-700 p-3 min-h-0">
      <h3 className="text-xs font-semibold text-slate-400 mb-2 shrink-0">LIVE CARDS</h3>
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {active.length === 0 && <p className="text-sm text-slate-500">Listening… cards appear here live.</p>}
        {active.map((c) => <LiveCard key={c.id} card={c} />)}
      </div>
      {history.length > 0 && (
        <details className="shrink-0 mt-2 text-xs text-slate-500">
          <summary className="cursor-pointer">history ({history.length})</summary>
          <div className="mt-1 space-y-1 max-h-24 overflow-y-auto">
            {history.map((c) => <div key={c.id} className="opacity-60">{c.title}</div>)}
          </div>
        </details>
      )}
    </div>
  );
}
