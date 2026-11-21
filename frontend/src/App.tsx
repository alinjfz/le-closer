import { useState } from "react";
import Setup from "./pages/Setup";
import LiveCall from "./pages/LiveCall";
import PostCall from "./pages/PostCall";
import { useEvents } from "./lib/useEvents";
import { useCallStore } from "./store/callStore";

type Screen = "setup" | "live" | "post";

export default function App() {
  const [screen, setScreen] = useState<Screen>("setup");
  const call = useCallStore((s) => s.call);

  useEvents(screen === "setup" ? null : call?.call_id ?? null);

  if (screen === "setup") return <Setup onStart={() => setScreen("live")} />;
  if (screen === "post") return <PostCall onBack={() => setScreen("live")} onNewCall={() => { useCallStore.getState().reset(); setScreen("setup"); }} />;
  return <LiveCall onEndCall={() => setScreen("post")} />;
}
