import { useState } from "react";
import { useCallStore } from "../store/callStore";
import { api } from "../lib/api";

/**Demo controls: text injection + pre-recorded script playback (D12).*/
export default function AudioControls() {
  const call = useCallStore((s) => s.call);
  const [speaker, setSpeaker] = useState<"rep" | "client">("client");
  const [text, setText] = useState("");
  if (!call) return null;

  const inject = () => {
    if (!text.trim()) return;
    api(`/calls/${call.call_id}/inject`, "POST", { speaker, text });
    setText("");
  };
  const playDemo = () => api(`/calls/${call.call_id}/demo/play`, "POST", { delay: 2.5 });

  if (!call.demo) return null;

  return (
    <div className="flex items-center gap-2">
      <select value={speaker} onChange={(e) => setSpeaker(e.target.value as "rep" | "client")}
        className="bg-ink border border-slate-600 rounded px-2 py-1 text-sm">
        <option value="client">client</option>
        <option value="rep">rep</option>
      </select>
      <input value={text} onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && inject()}
        placeholder="Inject a line…"
        className="flex-1 bg-ink border border-slate-600 rounded px-2 py-1 text-sm outline-none focus:border-accent" />
      <button onClick={inject} className="bg-slate-700 hover:bg-slate-600 text-sm px-3 py-1 rounded">Inject</button>
      <button onClick={playDemo} className="bg-accent text-ink text-sm px-3 py-1 rounded font-medium">▶ Play demo script</button>
    </div>
  );
}
