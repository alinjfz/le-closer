import { useCallStore } from "../../store/callStore";

export default function NumbersPanel() {
  const call = useCallStore((s) => s.call);
  const facts = call?.facts;
  const n = call?.numbers;

  const rows: [string, string][] = [
    ["Seats", facts?.seats != null ? String(facts.seats) : "—"],
    ["List price / seat", facts?.list_price_per_seat ? `€${facts.list_price_per_seat}/mo` : "€30/mo (default)"],
    ["Requested discount", facts?.requested_discount_pct != null ? `${facts.requested_discount_pct}%` : "—"],
    ["Discount floor", `${n?.discount_floor_pct ?? 10}%`],
    ["Deal value", n?.deal_value != null ? `€${n.deal_value.toLocaleString()}` : "—"],
    ["Price at requested disc.", n?.price_at_requested_discount != null ? `€${n.price_at_requested_discount.toLocaleString()}/yr` : "—"],
    ["Margin", n?.margin_pct != null ? `${n.margin_pct.toFixed(1)}%` : "—"],
    ["Client ROI", n?.client_roi_estimate != null ? `${n.client_roi_estimate.toFixed(1)}×` : "—"],
    ["Budget mentioned", facts?.budget != null ? `€${facts.budget.toLocaleString()}` : "—"],
  ];

  return (
    <div className="h-full overflow-y-auto text-sm">
      <div className={`mb-2 text-xs px-2 py-1 rounded ${n?.within_guardrails ? "bg-green-800" : "bg-red-800"}`}>
        {n?.within_guardrails ? "✓ within guardrails" : "⚠ outside guardrails — negotiate"}
      </div>
      <table className="w-full text-left">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-b border-slate-800">
              <td className="py-1.5 pr-2 text-slate-400 text-xs">{k}</td>
              <td className="py-1.5 font-medium">{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {facts?.requested_discount_pct != null && n && facts.requested_discount_pct > n.discount_floor_pct && (
        <div className="mt-3 bg-ink border border-amber-600 rounded-lg p-2 text-xs text-amber-200">
          🤝 Suggestion: offer {n.discount_floor_pct}% in exchange for a 2-year contract.
        </div>
      )}
    </div>
  );
}
