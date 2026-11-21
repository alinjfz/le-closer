import { useState } from "react";
import TodoList from "./TodoList";
import MindMap from "./MindMap";
import PrototypeFrame from "./PrototypeFrame";
import NumbersPanel from "./NumbersPanel";

const TABS = ["To-do", "Mind map", "Prototype", "Numbers"] as const;

export default function RightTabs() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("To-do");
  return (
    <div className="h-full flex flex-col bg-panel rounded-xl border border-slate-700 min-h-0">
      <div className="flex border-b border-slate-700 shrink-0">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 text-xs py-2 ${tab === t ? "text-accent border-b-2 border-accent" : "text-slate-400 hover:text-slate-200"}`}>
            {t}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 p-2">
        {tab === "To-do" && <TodoList />}
        {tab === "Mind map" && <MindMap />}
        {tab === "Prototype" && <PrototypeFrame />}
        {tab === "Numbers" && <NumbersPanel />}
      </div>
    </div>
  );
}
