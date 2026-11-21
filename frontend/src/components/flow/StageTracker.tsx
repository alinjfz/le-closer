import { useCallStore } from "../../store/callStore";

const STAGES = ["rapport", "discovery", "demo", "objections", "pricing", "close"];

export default function StageTracker() {
  const stage = useCallStore((s) => s.call?.flow.stage ?? "rapport");
  const idx = STAGES.indexOf(stage);
  return (
    <div className="mb-3">
      <div className="text-xs text-slate-500 mb-1">Stage: <span className="text-accent font-medium capitalize">{stage}</span></div>
      <div className="flex gap-1">
        {STAGES.map((s, i) => (
          <div key={s} title={s} className={`h-1.5 flex-1 rounded ${i < idx ? "bg-green-500" : i === idx ? "bg-accent animate-pulse-dot" : "bg-slate-700"}`} />
        ))}
      </div>
      <div className="flex justify-between text-[9px] text-slate-500 mt-0.5 capitalize">
        {STAGES.map((s) => <span key={s}>{s}</span>)}
      </div>
    </div>
  );
}
