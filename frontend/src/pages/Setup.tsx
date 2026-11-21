import { useState } from "react";
import { api } from "../lib/api";
import { useCallStore } from "../store/callStore";

export default function Setup({ onStart }: { onStart: () => void }) {
  const [company, setCompany] = useState("Müller Logistik GmbH");
  const [person, setPerson] = useState("Dr. Anna Weber, Head of IT");
  const [repName, setRepName] = useState("Alex");
  const [meetUrl, setMeetUrl] = useState("");
  const [demo, setDemo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const setCall = useCallStore((s) => s.setCall);

  const start = async () => {
    setLoading(true);
    setError("");
    const res = await api("/calls", "POST", {
      client: {
        company,
        country: "DE",
        industry: "Logistics",
        people: [{ name: person.split(",")[0], title: person.split(",")[1]?.trim() || "" }],
      },
      mode: "sales",
      demo,
      start_bot: false,
      meet_url: meetUrl || null,
      rep_name: repName,
    });
    if (res.call_id) {
      setCall(res.state);
      onStart();
    } else {
      setError(res.error || "failed to create call");
    }
    setLoading(false);
  };

  const resumeLatest = async () => {
    setLoading(true);
    const state = await api("/calls/latest");
    if (state.call_id) {
      setCall(state);
      onStart();
    } else {
      setError("No existing call yet — start a new one.");
    }
    setLoading(false);
  };

  const createSpace = async () => {
    setLoading(true);
    setError("");
    const res = await api("/calls", "POST", {
      client: { company, country: "DE", industry: "Logistics",
        people: [{ name: person.split(",")[0], title: person.split(",")[1]?.trim() || "" }] },
      mode: "sales", demo: false, meet_url: null, rep_name: repName,
    });
    if (res.call_id) {
      const space = await api(`/calls/${res.call_id}/meet/create`, "POST", {});
      if (space.meet_url) {
        setMeetUrl(space.meet_url);
        setDemo(false);
        setLoading(false);
        return;
      }
      setError(space.error || "Meet API unavailable — paste a Meet link instead (needs GOOGLE_APPLICATION_CREDENTIALS).");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-full flex items-center justify-center p-8">
      <div className="w-full max-w-lg bg-panel rounded-2xl p-8 shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-accent mb-1">Le Closer</h1>
        <p className="text-slate-400 mb-6">Transcribe your Google Meet by sharing its tab audio from your browser.</p>

        <label className="block text-sm text-slate-400 mb-1">Client company</label>
        <input value={company} onChange={(e) => setCompany(e.target.value)}
          className="w-full mb-4 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />

        <label className="block text-sm text-slate-400 mb-1">Key contact (name, title)</label>
        <input value={person} onChange={(e) => setPerson(e.target.value)}
          className="w-full mb-4 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />

        <label className="block text-sm text-slate-400 mb-1">Your name (shown in transcript)</label>
        <input value={repName} onChange={(e) => setRepName(e.target.value)}
          className="w-full mb-4 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />

        <label className="block text-sm text-slate-400 mb-1">Google Meet link (optional reference)</label>
        <div className="flex gap-2 mb-3">
          <input value={meetUrl} onChange={(e) => { setMeetUrl(e.target.value); if (e.target.value.trim()) setDemo(false); }} placeholder="https://meet.google.com/xxx-yyyy-zzz"
            className="flex-1 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />
          <button onClick={createSpace} disabled={loading} title="Create a fresh Meet space via the Meet API"
            className="border border-slate-600 hover:border-accent text-sm px-3 rounded-lg whitespace-nowrap">
            + Create space
          </button>
        </div>

        <label className="flex items-center gap-2 mb-2 text-sm text-slate-300">
          <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} className="accent-amber-500" />
          Demo mode (scripted call)
        </label>
        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <button onClick={start} disabled={loading}
          className="w-full bg-accent text-ink font-semibold rounded-lg py-3 hover:brightness-110 disabled:opacity-50">
          {loading ? "Starting…" : demo ? "Start demo call ▶" : "Start live dashboard"}
        </button>
        {!demo && (
          <p className="text-xs text-slate-500 mt-3">
            Next, confirm participant consent and share your Meet tab audio. No bot joins the meeting.
          </p>
        )}
        <button onClick={resumeLatest} disabled={loading}
          className="w-full mt-2 border border-slate-600 hover:border-accent text-sm rounded-lg py-2 disabled:opacity-50">
          Resume latest call ↻
        </button>
      </div>
    </div>
  );
}
