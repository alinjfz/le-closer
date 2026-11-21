import { useRef, useState } from "react";
import TopBar from "../components/TopBar";
import FlowPanel from "../components/flow/FlowPanel";
import CardsPanel from "../components/cards/CardsPanel";
import RightTabs from "../components/tabs/RightTabs";
import ActivityBar from "../components/ActivityBar";
import AudioControls from "../components/AudioControls";
import { useEvents } from "../lib/useEvents";

export default function LiveCall({ callId, onEndCall }: { callId: string | null; onEndCall: () => void }) {
  useEvents(callId);
  const [rightW, setRightW] = useState(360);
  const dragging = useRef(false);

  const onMove = (e: MouseEvent) => {
    if (!dragging.current) return;
    const w = window.innerWidth - e.clientX - 16;
    setRightW(Math.min(640, Math.max(260, w)));
  };
  const onUp = () => { dragging.current = false; window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  const startDrag = () => {
    dragging.current = true;
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  return (
    <div className="h-full flex flex-col">
      <TopBar onEndCall={onEndCall} />
      <div className="flex-1 flex gap-3 p-3 min-h-0">
        <div className="flex-[3] min-w-0 min-h-0"><FlowPanel /></div>
        <div className="flex-[6] min-w-0 min-h-0"><CardsPanel /></div>
        <div className="w-1.5 cursor-col-resize bg-slate-700 hover:bg-accent rounded shrink-0" onMouseDown={startDrag} title="drag to resize panel" />
        <div style={{ width: rightW }} className="shrink-0 min-h-0"><RightTabs /></div>
      </div>
      <ActivityBar />
      <div className="px-4 py-2 bg-panel border-t border-slate-700">
        <AudioControls />
      </div>
    </div>
  );
}
