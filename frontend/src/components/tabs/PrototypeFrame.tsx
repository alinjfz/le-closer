import { useState } from "react";
import { Monitor, Smartphone, PanelsTopLeft } from "lucide-react";
import { useCallStore } from "../../store/callStore";

export default function PrototypeFrame() {
  const prototypes = useCallStore((s) => s.call?.prototypes ?? []);
  const [selected, setSelected] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const current = prototypes.find((p) => p.id === selected) ?? prototypes[prototypes.length - 1];
  if (!current) return <div className="tool-empty"><PanelsTopLeft size={30} /><h3>Turn an idea into a preview</h3><p>Choose “Prototype” on an integration suggestion to build an interactive example during your call.</p><span>Use the expand button above for more room to explore.</span></div>;
  return <div className="prototype-tool">
    <div className="prototype-picker"><label htmlFor="prototype-select">Preview</label><select id="prototype-select" value={current.id} onChange={(e) => setSelected(e.target.value)}>{prototypes.map((p, i) => <option key={p.id} value={p.id}>{i + 1}. {p.title}</option>)}</select></div>
    <div className="tool-toolbar"><div className="tool-switch" role="group" aria-label="Preview device"><button onClick={() => setDevice("desktop")} aria-pressed={device === "desktop"}><Monitor size={15} /> Desktop</button><button onClick={() => setDevice("mobile")} aria-pressed={device === "mobile"}><Smartphone size={15} /> Mobile</button></div></div>
    <div className="prototype-stage"><iframe key={current.id} title={current.title} sandbox="allow-scripts" srcDoc={current.html} className={device === "mobile" ? "preview-mobile" : "preview-desktop"} /></div>
    <p className="map-hint">Interactive concept preview · {device === "mobile" ? "Mobile width: 375px" : "Adapts to the available workspace"}</p>
  </div>;
}
