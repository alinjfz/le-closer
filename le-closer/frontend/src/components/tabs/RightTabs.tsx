import TodoList from "./TodoList";
import MindMap from "./MindMap";
import PrototypeFrame from "./PrototypeFrame";
import NumbersPanel from "./NumbersPanel";
import { useCallStore } from "../../store/callStore";

const TABS = ["To-do", "Mind map", "Prototype", "Numbers"] as const;

export default function RightTabs() {
  const tab = useCallStore((s) => s.activeTab);
  const setTab = useCallStore((s) => s.setTab);
  const active = (TABS as readonly string[]).includes(tab) ? tab : "To-do";

  return (
    <div className="h-full flex flex-col bg-panel rounded-xl border border-slate-700 min-h-0">
      <div className="flex border-b border-slate-700 shrink-0">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 text-xs py-2 ${active === t ? "text-accent border-b-2 border-accent" : "text-slate-400 hover:text-slate-200"}`}>
            {t}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 p-2">
        {active === "To-do" && <TodoList />}
        {active === "Mind map" && <MindMap />}
        {active === "Prototype" && <PrototypeFrame />}
        {active === "Numbers" && <NumbersPanel />}
      </div>
    </div>
  );
}
