import { useState } from "react";
import { Pin, ThumbsUp, X } from "lucide-react";
import RichText from "../RichText";
import type { Card } from "../../store/callStore";
import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

const KIND_LABEL: Record<string, string> = {
  answer: "Answer", integration: "Integration", objection: "Objection", competitor: "Competitor",
  suggested_question: "Follow-up", cultural: "Language & context", gap: "Open question",
  prototype: "Prototype", research: "Research", negotiation: "Negotiation", deal: "Deal",
};

export default function LiveCard({ card }: { card: Card }) {
  const call = useCallStore((s) => s.call);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const kind = KIND_LABEL[card.kind] ?? "Suggestion";

  const act = (action: string) => {
    if (call) api(`/calls/${call.call_id}/cards/${card.id}`, "POST", { action });
  };
  const prototype = async () => {
    if (!call || generating) return;
    setGenerating(true); setError("");
    const result = await api(`/calls/${call.call_id}/prototype`, "POST", {
      topic: card.meta?.prototype_topic || card.title, kind: "code", based_on_call: true,
    });
    if (result.error) setError(result.error);
    else useCallStore.getState().setTab("Prototype");
    setGenerating(false);
  };

  return (
    <div className={`copilot-suggestion ${card.kind === "suggested_question" ? "suggestion-followup" : ""}`}>
      <p className="suggestion-kind mb-2">{kind}</p>
      <div className="flex items-center gap-2 mb-2">
        <span className="font-medium text-sm flex-1">{card.title}</span>
        <span className="text-xs text-muted" title="Model confidence">{Math.round(card.confidence * 100)}%</span>
      </div>
      <RichText text={card.body} collapsible />
      {card.sources.length > 0 && (
        <p className="text-xs text-muted mt-1">sources: {card.sources.join(" · ")}</p>
      )}
      <div className="flex flex-wrap gap-4 mt-4 pt-3 border-t border-line text-xs">
        <button onClick={() => act("useful")} className="text-muted hover:text-success inline-flex gap-1.5 items-center"><ThumbsUp size={14} /> Useful</button>
        <button onClick={() => act("dismiss")} className="text-muted hover:text-danger inline-flex gap-1.5 items-center"><X size={14} /> Dismiss</button>
        <button onClick={() => act("pin")} className="text-muted hover:text-accent inline-flex gap-1.5 items-center"><Pin size={14} /> Pin</button>
        {card.meta?.prototype_available && !call?.ended && (
          <button onClick={() => void prototype()} disabled={generating || call?.tasks.some(task => task.origin === "prototype" && task.status === "working")} className="ml-auto text-accent hover:underline">{generating ? "Starting…" : "Generate"}</button>
        )}
      </div>
      {error && <p role="alert" className="text-danger text-sm mt-3">{error}</p>}
    </div>
  );
}
