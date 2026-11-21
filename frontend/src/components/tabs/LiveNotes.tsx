import { useEffect, useState } from "react";
import { useCallStore } from "../../store/callStore";
import RichText from "../RichText";
import { api } from "../../lib/api";

export default function LiveNotes() {
  const call = useCallStore(s => s.call);
  const [text, setText] = useState(call?.personal_notes || "");
  const [saved, setSaved] = useState(call?.personal_notes || "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (text === saved) { setText(call?.personal_notes || ""); setSaved(call?.personal_notes || ""); }
  }, [call?.personal_notes]);
  if (!call) return null;
  return <div className="live-notes">
    <p className="text-muted text-sm">{call.ended ? "Final call notes" : "Notes update as the conversation unfolds. Confirmed actions are checked in Actions."}</p>
    <div className="notes-markdown" aria-live="polite"><RichText text={call.notes?.markdown || "Waiting for the conversation…"} /></div>
    <label htmlFor="personal-notes">Your notes</label>
    <textarea id="personal-notes" maxLength={20000} rows={16} value={text} onChange={e => setText(e.target.value)} placeholder="Add context, reminders or corrections…" />
    <button disabled={pending || text === saved} onClick={async () => {
      setPending(true); setError("");
      const result = await api(`/calls/${call.call_id}/notes/personal`, "POST", { text });
      if (result.error) setError(result.error); else { setSaved(text); useCallStore.getState().applyEvent("notes.personal", text); }
      setPending(false);
    }}>{pending ? "Saving…" : text === saved ? "Saved" : "Save your notes"}</button>
    {error && <p role="alert" className="text-danger">{error}</p>}
  </div>;
}
