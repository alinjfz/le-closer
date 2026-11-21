import { useCallStore } from "../../store/callStore";
const STAGES = ["rapport", "discovery", "demo", "objections", "pricing", "close"];
export default function StageTracker() {
  const stage = useCallStore((s) => s.call?.flow.stage ?? "rapport");
  const idx = STAGES.indexOf(stage);
  return <div className="mb-5"><div className="flex justify-between mb-3 text-sm"><span className="capitalize text-accent font-medium">{stage}</span><span className="text-slate-400">{idx >= 0 ? `${idx + 1} of ${STAGES.length} stages` : "Current stage"}</span></div><div className="flex gap-1.5" aria-label={`Current stage: ${stage}`}>{STAGES.map((s, i) => <div key={s} title={s} className={`h-1 flex-1 rounded ${i < idx ? "bg-green-500" : i === idx ? "bg-accent" : "bg-slate-700"}`} />)}</div></div>;
}
