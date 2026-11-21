import { useState } from "react";
import { AudioLines, Radio, Play, RotateCcw, Check, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useCallStore } from "../store/callStore";

export default function Setup({ onStart }: { onStart: () => void }) {
  const [company, setCompany] = useState("NordWerk Maschinenbau AG");
  const [person, setPerson] = useState("Dr. Anna Weber, Head of IT");
  const [repName, setRepName] = useState("Alex");
  const [meetUrl, setMeetUrl] = useState("");
  const [demo, setDemo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const setCall = useCallStore((s) => s.setCall);

  const start = async () => {
    if (!company.trim() || !person.trim() || !repName.trim()) {
      setError("Add a company, contact, and your name to continue.");
      return;
    }
    setLoading(true);
    setError("");
    const res = await api("/calls", "POST", {
      client: {
        company,
        country: "DE",
        industry: "Manufacturing",
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
    setError("");
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
      client: { company, country: "DE", industry: "Manufacturing",
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
    <div className="setup-page">
      <header className="setup-header">
        <a className="brand" href="/" aria-label="Le Closer home"><AudioLines size={25} /><span>Le Closer<span className="brand-period">.</span></span></a>
        <span className="text-sm text-muted">Your sales call copilot</span>
      </header>
      <main className="setup-main">
        <div className="setup-intro">
          <span className="eyebrow">CALL WORKSPACE</span>
          <h1>Good conversations.<br /><span className="text-accent">Better next steps.</span></h1>
          <p>Stay with your client. Le Closer keeps track of the conversation, finds answers, and captures what comes next.</p>
          <div className="setup-journey">
            <div><span className="journey-marker"><Check size={16} /></span><section><h2>Prepare your call</h2><p>Add your client and choose how to join.</p></section></div>
            <div><span className="journey-marker">2</span><section><h2>Get help in the moment</h2><p>See the transcript, suggestions, and action items as you talk.</p></section></div>
            <div><span className="journey-marker">3</span><section><h2>Leave with a follow-up</h2><p>Review call notes and approve your follow-up email.</p></section></div>
          </div>
          <p className="setup-footnote">You control audio capture and approve follow-up emails before they’re sent.</p>
        </div>
        <form className="setup-form" onSubmit={(event) => { event.preventDefault(); void start(); }}>
          <div className="mb-6"><h2 className="text-2xl font-semibold tracking-tight">Set up your call</h2><p className="text-sm text-muted mt-2">A little context helps your copilot get started.</p></div>
          <fieldset disabled={loading} className="space-y-6 min-w-0">
            <legend className="sr-only">Call details</legend>
            <div className="mode-picker" role="group" aria-label="Call mode">
              <button type="button" aria-pressed={!demo} onClick={() => setDemo(false)} className={!demo ? "selected" : ""}><Radio size={18} /><span>Live call<small>Use meeting audio</small></span>{!demo && <Check size={16} className="ml-auto" />}</button>
              <button type="button" aria-pressed={demo} onClick={() => setDemo(true)} className={demo ? "selected" : ""}><Play size={18} /><span>Try a demo<small>Use a sample script</small></span>{demo && <Check size={16} className="ml-auto" />}</button>
            </div>
            <div className="space-y-4">
              <label className="field-label" htmlFor="company">Client company<input id="company" required value={company} onChange={(e) => setCompany(e.target.value)} autoComplete="organization" /></label>
              <label className="field-label" htmlFor="contact">Key contact <span className="field-hint">Name, job title</span><input id="contact" required value={person} onChange={(e) => setPerson(e.target.value)} /></label>
              <label className="field-label" htmlFor="rep">Your name<input id="rep" required value={repName} onChange={(e) => setRepName(e.target.value)} autoComplete="given-name" /></label>
            </div>
            {!demo && <div className="meeting-field">
              <label className="field-label" htmlFor="meet">Google Meet link <span className="field-hint">Optional</span></label>
              <div className="flex gap-2 mt-2"><input id="meet" type="url" value={meetUrl} onChange={(e) => setMeetUrl(e.target.value)} placeholder="https://meet.google.com/…" className="min-w-0 flex-1" /><button type="button" onClick={createSpace} className="secondary-button whitespace-nowrap" title="Create a meeting with Google Meet">Create link</button></div>
              <p className="text-xs text-muted mt-2 leading-relaxed">Keep a meeting link for reference. You’ll share tab audio after opening the workspace.</p>
            </div>}
          </fieldset>
          {error && <p role="alert" className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error}</p>}
          <button type="submit" disabled={loading} className="primary-button w-full mt-6">{loading ? <><Loader2 size={18} className="animate-spin" /> Preparing workspace…</> : demo ? <><Play size={17} /> Open demo workspace</> : <><Radio size={17} /> Open call workspace</>}</button>
          <p className="text-xs text-muted text-center mt-3">{demo ? "Explore with a scripted conversation. No microphone needed." : "Audio starts only when you share it. No bot joins your call."}</p>
          <div className="resume-row"><span>Picking up where you left off?</span><button type="button" onClick={resumeLatest} disabled={loading}><RotateCcw size={14} /> Resume latest call</button></div>
        </form>
      </main>
      <footer className="setup-footer">LE CLOSER <span>Present in the conversation. Ready for the next step.</span></footer>
    </div>
  );
}
