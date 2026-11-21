import { useCallStore } from "../store/callStore";
import { api } from "../lib/api";

export default function PostCall({ onBack }: { onBack: () => void }) {
  const call = useCallStore((s) => s.call);
  if (!call) return null;

  const decide = (decision: string) => api(`/calls/${call.call_id}/followup/decision`, "POST", { decision });

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-accent">Post-call notes</h1>
          <button onClick={onBack} className="text-sm text-slate-400 hover:text-slate-200">← back to call</button>
        </div>

        <section className="bg-panel rounded-xl p-5 border border-slate-700">
          <h2 className="font-semibold mb-2">Summary & details</h2>
          <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans">
            {call.notes?.markdown || "Generating notes…"}
          </pre>
        </section>

        <section className="bg-panel rounded-xl p-5 border border-slate-700">
          <h2 className="font-semibold mb-2">Follow-up email</h2>
          <div className="bg-ink rounded-lg p-4 text-sm whitespace-pre-wrap border border-slate-700 mb-3">
            {call.followup_draft || "Drafting…"}
          </div>
          <div className="flex gap-2 items-center">
            {call.followup_status === "awaiting_approval" && (
              <>
                <button onClick={() => decide("approve")} className="bg-accent text-ink px-4 py-2 rounded-lg font-medium">Approve & send</button>
                <button onClick={() => decide("reject")} className="border border-slate-600 px-4 py-2 rounded-lg">Reject</button>
              </>
            )}
            <span className="text-sm text-slate-400">status: {call.followup_status}</span>
          </div>
        </section>

        <section className="bg-panel rounded-xl p-5 border border-slate-700">
          <h2 className="font-semibold mb-2">Action items</h2>
          <ul className="space-y-1 text-sm">
            {call.tasks.map((t) => (
              <li key={t.id} className="flex gap-2">
                <span className="text-accent">☐</span> {t.title}
                <span className="text-slate-500">({t.owner} · {t.status})</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
