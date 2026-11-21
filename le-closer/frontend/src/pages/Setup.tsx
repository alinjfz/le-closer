import { useState } from "react";
import { api } from "../lib/api";
import { useCallStore } from "../store/callStore";

export default function Setup({ onStart }: { onStart: () => void }) {
  const [company, setCompany] = useState("Müller Logistik GmbH");
  const [person, setPerson] = useState("Dr. Anna Weber, Head of IT");
  const [demo, setDemo] = useState(true);
  const [loading, setLoading] = useState(false);
  const setCall = useCallStore((s) => s.setCall);

  const start = async () => {
    setLoading(true);
    const res = await api("/calls", "POST", {
      client: {
        company,
        country: "DE",
        industry: "Logistics",
        people: [{ name: person.split(",")[0], title: person.split(",")[1]?.trim() || "" }],
      },
      mode: "sales",
      demo,
    });
    if (res.call_id) {
      setCall(res.state);
      onStart();
    }
    setLoading(false);
  };

  return (
    <div className="min-h-full flex items-center justify-center p-8">
      <div className="w-full max-w-lg bg-panel rounded-2xl p-8 shadow-2xl border border-slate-700">
        <h1 className="text-3xl font-bold text-accent mb-1">Le Closer</h1>
        <p className="text-slate-400 mb-6">Live multi-agent sales copilot — it doesn't just listen, it acts.</p>

        <label className="block text-sm text-slate-400 mb-1">Client company</label>
        <input value={company} onChange={(e) => setCompany(e.target.value)}
          className="w-full mb-4 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />

        <label className="block text-sm text-slate-400 mb-1">Key contact (name, title)</label>
        <input value={person} onChange={(e) => setPerson(e.target.value)}
          className="w-full mb-4 bg-ink border border-slate-600 rounded-lg px-3 py-2 outline-none focus:border-accent" />

        <label className="flex items-center gap-2 mb-6 text-sm text-slate-300">
          <input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} className="accent-amber-500" />
          Demo mode (pre-recorded call + text injection, no mic needed)
        </label>

        <button onClick={start} disabled={loading}
          className="w-full bg-accent text-ink font-semibold rounded-lg py-3 hover:brightness-110 disabled:opacity-50">
          {loading ? "Starting…" : "Start call ▶"}
        </button>
      </div>
    </div>
  );
}
