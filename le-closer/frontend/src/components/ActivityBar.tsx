import { useEffect, useRef } from "react";
import { useCallStore } from "../store/callStore";

const STATUS_ICON: Record<string, string> = {
  info: "·", working: "⟳", done: "✓", error: "✗",
};

export default function ActivityBar() {
  const activity = useCallStore((s) => s.call?.activity ?? []);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ left: ref.current.scrollWidth }); }, [activity.length]);

  return (
    <div ref={ref} className="flex gap-4 overflow-x-auto px-4 py-1.5 bg-panel border-t border-slate-700 text-xs text-slate-400 whitespace-nowrap">
      <span className="font-semibold text-slate-300 shrink-0">AGENT ACTIVITY</span>
      {activity.slice(-14).map((a, i) => (
        <span key={i} className={a.status === "working" ? "text-accent" : a.status === "error" ? "text-red-400" : ""}>
          {STATUS_ICON[a.status]} {a.agent}: {a.message}
        </span>
      ))}
    </div>
  );
}
