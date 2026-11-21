import { useEffect, useState } from "react";
import { useCallStore } from "../store/callStore";
import { AudioLines, PhoneOff, ExternalLink, Loader2 } from "lucide-react";
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
  const m = Math.floor(Math.max(0, elapsed) / 60), s = Math.floor(Math.max(0, elapsed) % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TopBar({ onEndCall }: { onEndCall: () => void }) {
  const call = useCallStore((s) => s.call);
  const connected = useCallStore((s) => s.connected);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState("");
  const timer = useTimer(call?.started_at || Date.now() / 1000, !!call && !call.ended);
  if (!call) return null;
  const n = call.numbers;
  const bot = BOT_LABEL[call.bot_status] ?? BOT_LABEL.offline;


  const end = async () => {
    setEnding(true);
    setError("");
    const result = await api(`/calls/${call.call_id}/end`, "POST", {});
    setEnding(false);
    if (result.error) { setError(result.error); return; }
    useCallStore.getState().applyEvent("call.ended", {});
    onEndCall();
  };


  return (
    <header className="call-topbar">
      <div className="brand"><AudioLines size={25} /><span>Le Closer<span className="brand-period">.</span></span></div>
      <div className="call-identity"><h1 className="text-base font-semibold">{call.client.company}</h1><div className="call-status"><span>{call.ended ? "Call ended" : call.demo ? "Demo workspace" : "Live workspace"}</span>{!call.ended && <span className="font-mono">{timer}</span>}<span className={connected ? "text-green-400" : "text-amber-300"}>{connected ? "Connected" : "Reconnecting…"}</span></div></div>
      {call.meet_url && <a href={call.meet_url} target="_blank" rel="noreferrer" className="text-sm text-slate-300 flex gap-2 items-center hover:text-accent">Open Meet <ExternalLink size={14} /></a>}
      {["launching", "joining", "requested", "in_call", "capturing", "error"].includes(call.bot_status) && <span className={`text-xs px-2 py-1 rounded ${bot.cls}`} title={call.bot_detail}>{bot.text}</span>}
      {n?.deal_value != null && <div className="text-sm text-slate-400">Deal value <b className="text-slate-100 ml-2">€{n.deal_value.toLocaleString()}</b></div>}
      {n && !n.within_guardrails && <span className="text-sm text-red-300">Outside pricing guardrails</span>}
      <button onClick={call.ended ? onEndCall : end} disabled={ending} className={call.ended ? "secondary-button" : "call-end"}>{ending ? <Loader2 size={16} className="animate-spin" /> : !call.ended && <PhoneOff size={16} />}{call.ended ? "View call review" : ending ? "Ending call…" : "End & review"}</button>
      {error && <p role="alert" className="text-red-300 text-sm w-full">{error}</p>}
    </header>
  );
}
