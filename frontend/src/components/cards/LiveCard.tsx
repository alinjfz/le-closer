import { Pin, ThumbsUp, X } from "lucide-react";
import type { Card } from "../../store/callStore";
import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

const KIND_STYLE: Record<string, { icon: string; ring: string }> = {
  answer: { icon: "💡", ring: "border-sky-500" },
  integration: { icon: "🔌", ring: "border-violet-500" },
  objection: { icon: "🛡️", ring: "border-red-500" },
  competitor: { icon: "⚔️", ring: "border-orange-500" },
  suggested_question: { icon: "❓", ring: "border-green-500" },
  cultural: { icon: "🌍", ring: "border-teal-500" },
  gap: { icon: "🕳️", ring: "border-slate-500" },
  research: { icon: "🔍", ring: "border-blue-500" },
  negotiation: { icon: "🤝", ring: "border-amber-500" },
  deal: { icon: "💰", ring: "border-yellow-500" },
};

export default function LiveCard({ card }: { card: Card }) {
  const call = useCallStore((s) => s.call);
  const style = KIND_STYLE[card.kind] ?? { icon: "📌", ring: "border-slate-500" };

  const act = (action: string) => {
    if (call) api(`/calls/${call.call_id}/cards/${card.id}`, "POST", { action });
  };
  const prototype = () => {
    if (call) api(`/calls/${call.call_id}/prototype`, "POST", { topic: card.title });
  };

  return (
    <div className={`animate-slide-in bg-ink rounded-lg p-3 border-l-4 ${style.ring}`}>
      <div className="flex items-center gap-2 mb-1">
        <span>{style.icon}</span>
        <span className="font-medium text-sm flex-1">{card.title}</span>
        <span className="text-xs text-slate-400" title="Model confidence">{Math.round(card.confidence * 100)}%</span>
      </div>
      <p className="text-sm text-slate-300 whitespace-pre-wrap">{card.body}</p>
      {card.sources.length > 0 && (
        <p className="text-xs text-slate-400 mt-1">sources: {card.sources.join(" · ")}</p>
      )}
      <div className="flex flex-wrap gap-4 mt-4 pt-3 border-t border-slate-700 text-xs">
        <button onClick={() => act("useful")} className="text-slate-400 hover:text-green-400 inline-flex gap-1.5 items-center"><ThumbsUp size={14} /> Useful</button>
        <button onClick={() => act("dismiss")} className="text-slate-400 hover:text-red-400 inline-flex gap-1.5 items-center"><X size={14} /> Dismiss</button>
        <button onClick={() => act("pin")} className="text-slate-400 hover:text-accent inline-flex gap-1.5 items-center"><Pin size={14} /> Pin</button>
        {card.kind === "integration" && card.meta?.prototype_available && (
          <button onClick={prototype} className="ml-auto text-accent hover:underline">Prototype ▶</button>
        )}
      </div>
    </div>
  );
}
