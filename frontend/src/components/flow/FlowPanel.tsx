import { MessageSquareText } from "lucide-react";
import StageTracker from "./StageTracker";
import BantChecklist from "./BantChecklist";
import Transcript from "./Transcript";

export default function FlowPanel() {
  return (
    <div className="h-full flex flex-col gap-4 min-h-0">
      <section className="workspace-panel shrink-0"><div className="panel-heading"><h2>Conversation progress</h2></div><div className="p-4"><StageTracker /><BantChecklist /></div></section>
      <section className="workspace-panel flex-1 min-h-0"><div className="panel-heading"><div className="flex gap-2 items-center"><MessageSquareText size={17} className="text-slate-400" /><h2>Transcript</h2></div></div><Transcript /></section>
    </div>
  );
}
