import { useState } from "react";
import { Headphones } from "lucide-react";
import TopBar from "../components/TopBar";
import FlowPanel from "../components/flow/FlowPanel";
import CardsPanel from "../components/cards/CardsPanel";
import RightTabs from "../components/tabs/RightTabs";
import ActivityBar from "../components/ActivityBar";
import BrowserAudioControls from "../components/BrowserAudioControls";
import { useCallStore } from "../store/callStore";

const VIEWS = ["Conversation", "Copilot", "Call tools"] as const;
export default function LiveCall({ onEndCall }: { onEndCall: () => void }) {
  const [view, setView] = useState<typeof VIEWS[number]>("Copilot");
  const demo = useCallStore((s) => s.call?.demo);
  const ended = useCallStore((s) => s.call?.ended);
  return (
    <div className="live-page">
      <TopBar onEndCall={onEndCall} />
      <main className="live-main">
        {!ended && !demo && <section className="audio-setup">
          <div className="audio-heading"><Headphones size={19} className="text-accent" /><div><h2>Connect your call audio</h2><p>Confirm consent, then share the Google Meet tab with audio enabled.</p></div></div>
          <BrowserAudioControls />
        </section>}
        <nav className="mobile-views" aria-label="Workspace sections">{VIEWS.map((name) => <button key={name} aria-pressed={view === name} onClick={() => setView(name)}>{name}</button>)}</nav>
        <div className="workspace-grid">
          <section aria-label="Conversation" className={`workspace-conversation ${view === "Conversation" ? "mobile-active" : ""}`}><FlowPanel /></section>
          <section aria-label="Copilot suggestions" className={`workspace-copilot ${view === "Copilot" ? "mobile-active" : ""}`}><CardsPanel /></section>
          <aside aria-label="Call tools" className={`workspace-tools ${view === "Call tools" ? "mobile-active" : ""}`}><RightTabs /></aside>
        </div>
      </main>
      <ActivityBar />
    </div>
  );
}
