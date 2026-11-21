import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

const STATUS_ICON: Record<string, string> = {
  queued: "☐", working: "⟳", ready: "✓", done: "☑",
};

export default function TodoList() {
  const call = useCallStore((s) => s.call);
  const tasks = call?.tasks ?? [];

  const setDone = (id: string) => {
    if (call) api(`/calls/${call.call_id}/tasks/${id}`, "POST", { status: "done" });
  };

  return (
    <div className="h-full overflow-y-auto space-y-1.5 text-sm">
      {tasks.length === 0 && <p className="text-slate-500 text-sm">No to-dos yet — promises made on the call appear here.</p>}
      {tasks.map((t) => (
        <div key={t.id} className="bg-ink rounded-lg px-2.5 py-2 flex items-center gap-2 border border-slate-700">
          <span className={t.status === "working" ? "text-accent animate-pulse-dot" : "text-slate-300"}>
            {STATUS_ICON[t.status] ?? "☐"}
          </span>
          <span className={`flex-1 ${t.status === "done" ? "line-through opacity-50" : ""}`}>{t.title}</span>
          <span className="text-[10px] text-slate-500">{t.owner}</span>
          {t.status === "ready" && (
            <button onClick={() => setDone(t.id)} className="text-[10px] text-green-400 hover:underline">mark done</button>
          )}
        </div>
      ))}
    </div>
  );
}
