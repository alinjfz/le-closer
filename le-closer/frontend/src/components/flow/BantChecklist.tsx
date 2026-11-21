import { useCallStore } from "../../store/callStore";

const MARK: Record<string, { icon: string; cls: string }> = {
  known: { icon: "●", cls: "text-green-400" },
  partial: { icon: "◐", cls: "text-accent" },
  unknown: { icon: "○", cls: "text-slate-600" },
};

export default function BantChecklist() {
  const bant = useCallStore((s) => s.call?.flow.bant ?? {});
  return (
    <div>
      <div className="text-xs text-slate-500 mb-1">BANT</div>
      <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-xs capitalize">
        {Object.entries(bant).map(([k, v]) => (
          <span key={k} className="text-slate-300">
            <span className={MARK[v]?.cls ?? ""}>{MARK[v]?.icon ?? "○"} </span>{k}
          </span>
        ))}
      </div>
    </div>
  );
}
