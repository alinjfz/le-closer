import { useCallStore } from "../store/callStore";
import { api } from "../lib/api";

export default function TopBar({ onEndCall }: { onEndCall: () => void }) {
  const call = useCallStore((s) => s.call);
  const connected = useCallStore((s) => s.connected);
  if (!call) return null;
  const n = call.numbers;

  const end = async () => {
    await api(`/calls/${call.call_id}/end`, "POST", {});
    onEndCall();
  };

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-panel border-b border-slate-700">
      <span className="text-xl font-bold text-accent">LE CLOSER</span>
      <span className="text-sm text-slate-300">🇩🇪 {call.client.company}</span>
      <span className={`text-xs px-2 py-0.5 rounded-full ${connected ? "bg-green-600" : "bg-red-600"}`}>
        {connected ? "● LIVE" : "○ reconnecting"}
      </span>
      <div className="flex-1" />
      {n?.deal_value != null && (
        <span className="text-sm">Deal value <b className="text-accent">€{n.deal_value.toLocaleString()}</b></span>
      )}
      <span className="text-sm">Discount floor <b>{n?.discount_floor_pct ?? 10}%</b></span>
      {n && !n.within_guardrails && (
        <span className="text-xs bg-red-700 px-2 py-0.5 rounded-full">outside guardrails</span>
      )}
      <button onClick={end} className="bg-red-600 hover:bg-red-500 text-sm px-3 py-1.5 rounded-lg">End call</button>
    </div>
  );
}
