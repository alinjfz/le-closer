import { useState } from "react";
import { Monitor, Smartphone } from "lucide-react";
import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

export default function PrototypeFrame() {
  const call = useCallStore(s => s.call);
  const prototypes = call?.prototypes ?? [];
  const [selected, setSelected] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [view, setView] = useState<"preview" | "code">("preview");
  const [topic, setTopic] = useState("");
  const [kind, setKind] = useState<"code" | "image">("code");
  const [basedOnCall, setBasedOnCall] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const current = prototypes.find(p => p.id === selected) ?? prototypes[prototypes.length - 1];
  const generationActivity = [...(call?.activity || [])].reverse().find(entry => entry.agent === "Prototype agent");
  const working = call?.tasks.some(t => t.origin === "prototype" && t.status === "working");
  return <div className="prototype-tool">
    {!call?.ended && <form className="prototype-form" onSubmit={async e => {
      e.preventDefault(); if (!call || (!topic.trim() && !(kind === "image" && basedOnCall))) return;
      setPending(true); setError("");
      const result = await api(`/calls/${call.call_id}/prototype`, "POST", { topic: topic.trim(), kind, based_on_call: kind === "image" && basedOnCall });
      if (result.error) setError(result.error); else { setTopic(""); setSelected(null); setView("preview"); }
      setPending(false);
    }}><label htmlFor="prototype-brief">{kind === "image" ? "What image should we generate?" : "What should we prototype?"}</label>
      {kind === "image" && <label className="call-image-option"><input type="checkbox" checked={basedOnCall} onChange={e => setBasedOnCall(e.target.checked)} /> Based on our call, generate an image</label>}
      {kind === "image" && basedOnCall && <p className="text-sm text-muted">Uses the conversation and notes. Add optional direction below.</p>}<textarea id="prototype-brief" maxLength={2000} rows={3} value={topic} onChange={e => setTopic(e.target.value)} placeholder={kind === "image" && basedOnCall ? "Optional: style, viewpoint, or details to emphasize…" : "A shipment dashboard, a product concept…"} /><div className="tool-toolbar"><select aria-label="Prototype output" value={kind} onChange={e => setKind(e.target.value as "code" | "image")}><option value="code">Interactive app + code</option><option value="image">Product concept image</option></select><button disabled={pending || working || (!topic.trim() && !(kind === "image" && basedOnCall))}>{pending || working ? "Generating…" : "Generate"}</button></div></form>}
    {generationActivity?.status === "error" && <p role="alert" className="text-danger">{generationActivity.message}</p>}
    {error && <p role="alert" className="text-danger">{error}</p>}
    {working && <p role="status" className="text-sm text-muted">Your prototype is being built. Results appear here; generation failures appear in activity.</p>}
    {!current ? <div className="tool-empty"><h3>Turn an idea into a preview</h3><p>Describe the end product. The prototype uses requirements from your conversation.</p></div> : <>
      <div className="prototype-picker"><label htmlFor="prototype-select">Preview</label><select id="prototype-select" value={current.id} onChange={e => setSelected(e.target.value)}>{prototypes.map((p, i) => <option key={p.id} value={p.id}>{i + 1}. {p.title}</option>)}</select></div>
      {current.image_url ? <img src={current.image_url} alt={`Product concept: ${current.title}`} className="prototype-image" /> : <>
        <div className="tool-toolbar"><div className="tool-switch"><button aria-pressed={view === "preview"} onClick={() => setView("preview")}>Preview</button><button aria-pressed={view === "code"} onClick={() => setView("code")}>Code</button></div><div className="tool-switch" role="group" aria-label="Preview device"><button onClick={() => setDevice("desktop")} aria-pressed={device === "desktop"}><Monitor size={15} /> Desktop</button><button onClick={() => setDevice("mobile")} aria-pressed={device === "mobile"}><Smartphone size={15} /> Mobile</button></div></div>
        {view === "code" ? <pre className="prototype-code">{current.html}</pre> : <div className="prototype-stage"><iframe key={current.id} title={current.title} sandbox="allow-scripts" srcDoc={current.html} className={device === "mobile" ? "preview-mobile" : "preview-desktop"} /></div>}
      </>}
    </>}
  </div>;
}
