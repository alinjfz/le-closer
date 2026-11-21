import { useState } from "react";
import { useCallStore } from "../../store/callStore";
import { api } from "../../lib/api";

const LANGUAGES = { en: "English", fr: "French", de: "German", es: "Spanish", it: "Italian", pt: "Portuguese", ar: "Arabic", hi: "Hindi", zh: "Chinese", ja: "Japanese", ko: "Korean", nl: "Dutch", tr: "Turkish", pl: "Polish", uk: "Ukrainian" };

export default function TranscriptLanguage() {
  const call = useCallStore(s => s.call);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return <div className="transcript-language">
    <label>Translate to <select aria-label="Transcript translation language" value={call?.settings?.translation_language || ""} disabled={!call || call.ended || pending} onChange={async event => {
      if (!call) return;
      setPending(true); setError("");
      const result = await api(`/calls/${call.call_id}/assistant/settings`, "POST", { translation_language: event.target.value });
      if (result.error) setError(result.error);
      else useCallStore.getState().applyEvent("assistant.settings", result.settings);
      setPending(false);
    }}><option value="">Original only</option>{Object.entries(LANGUAGES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
    {error && <p role="alert" className="text-danger text-xs">{error}</p>}
  </div>;
}
