import { useCallStore } from "../../store/callStore";

const MARK: Record<string, { icon: string; cls: string }> = {
  known: { icon: "●", cls: "text-success" },
  partial: { icon: "◐", cls: "text-accent" },
  unknown: { icon: "○", cls: "text-muted" },
};

export default function BantChecklist() {
  const bant = useCallStore((s) => s.call?.flow.bant ?? {});
  return (
    <div>
      <div className="text-xs text-muted mb-2">Deal qualification</div>
      <div className="grid grid-cols-2 gap-x-2 gap-y-2 text-sm capitalize">
        {Object.entries(bant).map(([k, v]) => (
          <span key={k} title={`${k}: ${v}`} className="text-copy">
            <span className={MARK[v]?.cls ?? ""}>{MARK[v]?.icon ?? "○"} </span>{k}
          </span>
        ))}
      </div>
    </div>
  );
}
