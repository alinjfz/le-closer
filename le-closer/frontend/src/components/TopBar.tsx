import { useEffect, useState } from "react";
import { useCallStore } from "../store/callStore";
import { api } from "../lib/api";

const BOT_LABEL: Record<string, { icon: string; cls: string; text: string }> = {
  error: { icon: "⚠️", cls: "bg-red-700", text: "bot error — hover for details" },
  offline: { icon: "🤖", cls: "bg-slate-700", text: "bot offline" },
  launching: { icon: "🤖", cls: "bg-slate-600 animate-pulse", text: "bot launching…" },
  joining: { icon: "🤖", cls: "bg-slate-600 animate-pulse", text: "bot joining…" },
  requested: { icon: "🤖", cls: "bg-amber-700 animate-pulse", text: "bot waiting to be admitted" },
  waiting: { icon: "🤖", cls: "bg-amber-700", text: "bot not admitted" },
  in_call: { icon: "🤖", cls: "bg-green-700", text: "bot in call" },
  capturing: { icon: "🎙️", cls: "bg-green-600 animate-pulse", text: "bot capturing audio" },
  left: { icon: "🤖", cls: "bg-slate-700", text: "bot left" },
};

function useTimer(startedAt: number, running: boolean) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed(Date.now() / 1000 - startedAt), 1000);
    return () => clearInterval(t);
  }, [running, startedAt]);
  const m = Math.floor(elapsed / 60), s = Math.floor(elapsed % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TopBar({ onEndCall }: { onEndCall: () => void }) {
  const call = useCallStore((s) => s.call);
  const connected = useCallStore((s) => s.connected);
  if (!call) return null;
  const n = call.numbers;
  const bot = BOT_LABEL[call.bot_status] ?? BOT_LABEL.offline;
  const timer = useTimer(call.started_at || Date.now() / 1000, !call.ended);

  const end = async () => {
    await api(`/calls/${call.call_id}/end`, "POST", {});
    onEndCall();
  };


  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-panel border-b border-slate-700 flex-wrap">
      <span className="text-xl font-bold text-accent">LE CLOSER</span>
      <span className="text-sm text-slate-300">🇩🇪 {call.client.company}</span>
      {call.demo && <span className="text-xs bg-amber-800 px-2 py-1 rounded">Demo mode — scripted audio</span>}
      {["launching", "joining", "requested", "in_call", "capturing"].includes(call.bot_status) && <span className={`text-xs px-2 py-0.5 rounded-full ${bot.cls}`} title={call.bot_detail}>
        {bot.icon} {bot.text}
      </span>}
      {call.meet_url && (
        <a href={call.meet_url} target="_blank" rel="noreferrer" className="text-xs text-sky-400 hover:underline truncate max-w-[220px]">
          🔗 {call.meet_url.replace("https://", "")}
        </a>
      )}
      <span className={`text-xs px-2 py-0.5 rounded-full ${connected ? "bg-green-600" : "bg-red-600"}`}>
        {connected ? "● Dashboard connected" : "○ reconnecting"}
      </span>
      <span className="text-xs text-slate-400 font-mono">{timer}</span>
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
