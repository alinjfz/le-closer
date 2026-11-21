import StageTracker from "./StageTracker";
import BantChecklist from "./BantChecklist";
import Transcript from "./Transcript";

export default function FlowPanel() {
  return (
    <div className="h-full flex flex-col gap-3 min-h-0">
      <div className="bg-panel rounded-xl p-3 border border-slate-700 shrink-0">
        <h3 className="text-xs font-semibold text-slate-400 mb-2">CONVERSATION FLOW</h3>
        <StageTracker />
        <BantChecklist />
      </div>
      <div className="bg-panel rounded-xl p-3 border border-slate-700 flex-1 min-h-0 flex flex-col">
        <h3 className="text-xs font-semibold text-slate-400 mb-2 shrink-0">TRANSCRIPT</h3>
        <Transcript />
      </div>
    </div>
  );
}
