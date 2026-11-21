import { useCallStore } from "../../store/callStore";

const MARK: Record<string, { icon: string; cls: string }> = {
  known: { icon: "●", cls: "text-green-400" },
  partial: { icon: "◐", cls: "text-accent" },
  unknown: { icon: "○", cls: "text-slate-400" },
};

export default function BantChecklist() {
  const bant = useCallStore((s) => s.call?.flow.bant ?? {});
  return (
    <div>
      <div className="text-xs text-slate-400 mb-2">Deal qualification</div>
      <div className="grid grid-cols-2 gap-x-2 gap-y-2 text-sm capitalize">
        {Object.entries(bant).map(([k, v]) => (
          <span key={k} title={`${k}: ${v}`} className="text-slate-300">
            <span className={MARK[v]?.cls ?? ""}>{MARK[v]?.icon ?? "○"} </span>{k}
          </span>
        ))}
      </div>
    </div>
  );
}
