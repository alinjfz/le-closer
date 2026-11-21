import { useState } from "react";
import { Check, Circle, ListChecks, Loader2 } from "lucide-react";
import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

const STATUS: Record<string, string> = { queued: "To do", working: "In progress", ready: "Ready to review", done: "Completed" };
export default function TodoList() {
  const call = useCallStore((s) => s.call);
  const [filter, setFilter] = useState<"open" | "all">("open");
  const [pending, setPending] = useState<string[]>([]);
  const [error, setError] = useState("");
  const tasks = call?.tasks ?? [];
  const completed = tasks.filter((t) => t.status === "done").length;
  const visible = tasks.filter((t) => filter === "all" || t.status !== "done");
  const toggle = async (id: string, status: string) => {
    if (!call) return;
    setPending((ids) => [...ids, id]); setError("");
    const result = await api(`/calls/${call.call_id}/tasks/${id}`, "POST", { status });
    if (result.error) setError(result.error);
    else {
      const task = tasks.find((t) => t.id === id);
      if (task) useCallStore.getState().applyEvent("task.upsert", { ...task, status });
    }
    setPending((ids) => ids.filter((value) => value !== id));
  };
  return <div className="action-tool">
    <div className="tool-toolbar"><div className="tool-switch" role="group" aria-label="Filter action items"><button aria-pressed={filter === "open"} onClick={() => setFilter("open")}>Open <span>{tasks.length - completed}</span></button><button aria-pressed={filter === "all"} onClick={() => setFilter("all")}>All <span>{tasks.length}</span></button></div></div>
    {tasks.length > 0 && <div className="action-progress"><div className="flex justify-between text-xs text-muted mb-2"><span>Follow-through</span><span>{completed} of {tasks.length} complete</span></div><progress max={tasks.length} value={completed} aria-label="Action item completion" /></div>}
    {error && <p role="alert" className="text-sm text-danger mb-3">{error}</p>}
    <div className="action-list">{visible.length === 0 ? <div className="tool-empty"><ListChecks size={30} /><h3>{tasks.length ? "You’re all caught up" : "Keep every promise in view"}</h3><p>{tasks.length ? "All captured action items are complete. Choose All to review them." : "Promises and next steps from your call appear here, with an owner and progress."}</p></div> : visible.map((t) => <article key={t.id} className={`action-item ${t.status === "done" ? "is-done" : ""}`}>
      <button className="action-check" disabled={pending.includes(t.id) || t.status === "working"} aria-label={t.status === "done" ? `Reopen ${t.title}` : `Mark ${t.title} complete`} aria-pressed={t.status === "done"} onClick={() => void toggle(t.id, t.status === "done" ? "ready" : "done")}>{pending.includes(t.id) || t.status === "working" ? <Loader2 size={19} className="animate-spin" /> : t.status === "done" ? <Check size={19} /> : <Circle size={19} />}</button>
      <div className="min-w-0 flex-1"><h3>{t.title}</h3><div className="action-meta"><span className="capitalize">{t.owner}</span><span className={t.status === "working" ? "text-accent" : t.status === "ready" ? "text-accent" : ""}>{STATUS[t.status] || t.status}</span></div></div>
    </article>)}</div>
  </div>;
}
