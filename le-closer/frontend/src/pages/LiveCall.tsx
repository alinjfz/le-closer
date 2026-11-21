import TopBar from "../components/TopBar";
import FlowPanel from "../components/flow/FlowPanel";
import CardsPanel from "../components/cards/CardsPanel";
import RightTabs from "../components/tabs/RightTabs";
import ActivityBar from "../components/ActivityBar";
import AudioControls from "../components/AudioControls";
import { useEvents } from "../lib/useEvents";

export default function LiveCall({ callId, onEndCall }: { callId: string | null; onEndCall: () => void }) {
  useEvents(callId);
  return (
    <div className="h-full flex flex-col">
      <TopBar onEndCall={onEndCall} />
      <div className="flex-1 grid grid-cols-12 gap-3 p-3 min-h-0">
        <div className="col-span-3 min-h-0"><FlowPanel /></div>
        <div className="col-span-6 min-h-0"><CardsPanel /></div>
        <div className="col-span-3 min-h-0"><RightTabs /></div>
      </div>
      <ActivityBar />
      <div className="px-4 py-2 bg-panel border-t border-slate-700">
        <AudioControls />
      </div>
    </div>
  );
}
