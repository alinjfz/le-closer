import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Maximize2, X } from "lucide-react";
import TodoList from "./TodoList";
import MindMap from "./MindMap";
import PrototypeFrame from "./PrototypeFrame";
import NumbersPanel from "./NumbersPanel";
import { useCallStore } from "../../store/callStore";

const TABS = ["To-do", "Mind map", "Prototype", "Numbers"] as const;
const LABELS = { "To-do": "Actions", "Mind map": "Mind map", "Prototype": "Prototypes", "Numbers": "Deal numbers" };

export default function RightTabs() {
  const tab = useCallStore((s) => s.activeTab);
  const setTab = useCallStore((s) => s.setTab);
  const tasks = useCallStore((s) => s.call?.tasks ?? []);
  const prototypes = useCallStore((s) => s.call?.prototypes ?? []);
  const active = (TABS as readonly string[]).includes(tab) ? tab : "To-do";
  const [expanded, setExpanded] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const expandRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!expanded) return;
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { dialog?.close(); expandRef.current?.focus(); };
  }, [expanded]);
  const panel = <div className={`workspace-panel call-tools-panel ${expanded ? "tools-expanded" : ""}`}>
    <div className="panel-heading"><div><h2>{expanded ? "Call workspace" : "Call tools"}</h2>{expanded && <p className="text-sm text-slate-400 mt-1">Explore the details without leaving your call.</p>}</div><button ref={expanded ? undefined : expandRef} className="tool-icon-button" onClick={() => setExpanded(!expanded)} aria-label={expanded ? "Close expanded workspace" : "Expand call tools"} title={expanded ? "Close workspace (Esc)" : "Expand workspace"}>{expanded ? <X size={18} /> : <Maximize2 size={17} />}</button></div>
    <div className="call-tool-tabs" role="tablist" aria-label="Call tools">
      {TABS.map((t, i) => {
        const count = t === "To-do" ? tasks.filter((task) => task.status !== "done").length : t === "Prototype" ? prototypes.length : 0;
        return <button role="tab" aria-selected={active === t} aria-controls="call-tool-panel" id={`tool-tab-${i}`} tabIndex={active === t ? 0 : -1} key={t} onClick={() => setTab(t)} onKeyDown={(event) => {
          const next = event.key === "ArrowRight" ? (i + 1) % TABS.length : event.key === "ArrowLeft" ? (i + TABS.length - 1) % TABS.length : event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : -1;
          if (next >= 0) { event.preventDefault(); setTab(TABS[next]); const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]'); buttons?.[next]?.focus(); }
        }}>{LABELS[t]}{count > 0 && <span className="tab-count">{count}</span>}</button>;
      })}
    </div>
    <div className="call-tool-content" role="tabpanel" id="call-tool-panel" aria-labelledby={`tool-tab-${TABS.indexOf(active as typeof TABS[number])}`} tabIndex={0}>
      {active === "To-do" && <TodoList />}{active === "Mind map" && <MindMap />}{active === "Prototype" && <PrototypeFrame />}{active === "Numbers" && <NumbersPanel />}
    </div>
  </div>;
  return expanded ? createPortal(<dialog ref={dialogRef} className="tools-dialog" aria-label="Expanded call tools" onCancel={() => setExpanded(false)}>{panel}</dialog>, document.body) : panel;
}
