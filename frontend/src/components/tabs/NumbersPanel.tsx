import { Calculator, CheckCircle2, ShieldAlert } from "lucide-react";
import { useCallStore } from "../../store/callStore";

export default function NumbersPanel() {
  const call = useCallStore((s) => s.call);
  const facts = call?.facts;
  const n = call?.numbers;
  const money = (value?: number) => {
    if (value == null) return "Not captured";
    try { return new Intl.NumberFormat("en-GB", { style: "currency", currency: facts?.currency || "EUR", maximumFractionDigits: 2, minimumFractionDigits: 0 }).format(value); }
    catch { return `${value.toLocaleString()} ${facts?.currency || "EUR"}`; }
  };
  const rows: [string, string][] = [
    ["Seats", facts?.seats != null ? facts.seats.toLocaleString() : "Not captured"],
    ["Monthly price / seat", facts?.list_price_per_seat != null ? money(facts.list_price_per_seat) : "Default pricing applies"],
    ["Contract length", facts?.contract_years != null ? `${facts.contract_years} year${facts.contract_years === 1 ? "" : "s"}` : "1 year (default)"],
    ["Client budget", money(facts?.budget)],
    ["Requested discount", facts?.requested_discount_pct != null ? `${facts.requested_discount_pct}%` : "Not captured"],
    ["Discount limit", n ? `${n.discount_floor_pct}%` : "Awaiting deal details"],
    ["Estimated margin", n?.margin_pct != null ? `${n.margin_pct.toFixed(1)}%` : "Awaiting deal details"],
    ["Estimated client ROI", n?.client_roi_estimate != null ? `${n.client_roi_estimate.toFixed(1)}×` : "Awaiting deal details"],
  ];
  return <div className="numbers-tool">
    <div className="deal-summary"><div className="flex gap-2 items-center text-sm text-slate-400"><Calculator size={17} /><span>Total deal value</span></div><p className="deal-value">{n?.deal_value != null ? money(n.deal_value) : "—"}</p><p className="text-xs text-slate-400">{n?.deal_value != null ? "After requested discount, over the contract term" : "Mention seats and pricing to start building the deal."}</p>{n?.price_at_requested_discount != null && <div className="deal-annual"><span>Annual price after discount</span><strong>{money(n.price_at_requested_discount)}</strong></div>}</div>
    {n && <div className={`deal-guardrail ${n.within_guardrails ? "within" : "outside"}`}>{n.within_guardrails ? <CheckCircle2 size={19} /> : <ShieldAlert size={19} />}<div><strong>{n.within_guardrails ? "Within pricing limits" : "Discount needs attention"}</strong><p>{n.within_guardrails ? `Discounts up to ${n.discount_floor_pct}% are within the current limit.` : `The requested ${facts?.requested_discount_pct ?? 0}% exceeds the ${n.discount_floor_pct}% limit.`}</p></div></div>}
    <h3 className="tool-section-label">Deal breakdown</h3>
    <dl className="deal-breakdown">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd className={/Not captured|Awaiting|default|Default/.test(value) ? "is-missing" : ""}>{value}</dd></div>)}</dl>
    <p className="map-hint mt-4">Updates from the conversation. Calculations use captured facts and configured pricing defaults.</p>
  </div>;
}
