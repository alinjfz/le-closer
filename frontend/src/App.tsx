import { useState } from "react";
import Setup from "./pages/Setup";
import LiveCall from "./pages/LiveCall";
import PostCall from "./pages/PostCall";
import { useCallStore } from "./store/callStore";

type Screen = "setup" | "live" | "post";

export default function App() {
  const [screen, setScreen] = useState<Screen>("setup");
  const call = useCallStore((s) => s.call);

  if (screen === "setup") return <Setup onStart={() => setScreen("live")} />;
  if (screen === "post" || (call?.ended && call.notes)) return <PostCall onBack={() => setScreen("live")} />;
  return <LiveCall callId={call?.call_id ?? null} onEndCall={() => setScreen("post")} />;
}
