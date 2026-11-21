import { useState } from "react";
import { AudioLines, CheckCircle2, Loader2, FileText, Mail, ListChecks } from "lucide-react";
import { useCallStore } from "../store/callStore";
import { api } from "../lib/api";

const STATUS: Record<string, string> = { none: "Preparing draft", awaiting_approval: "Ready for your review", approved: "Approved", rejected: "Draft rejected", sent: "Email sent" };
export default function PostCall({ onBack, onNewCall }: { onBack: () => void; onNewCall: () => void }) {
  const call = useCallStore((s) => s.call);
  const applyEvent = useCallStore((s) => s.applyEvent);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!call) return null;
  const decide = async (decision: string) => {
    setBusy(true);
    setError("");
    const result = await api(`/calls/${call.call_id}/followup/decision`, "POST", { decision });
    if (result.error) setError(result.error);
    else {
      const state = await api(`/calls/${call.call_id}`);
      if (state.call_id) applyEvent("state.sync", state);
    }
    setBusy(false);
  };
  return (
    <main className="post-page"><div className="post-container">
      <header className="flex flex-wrap gap-4 justify-between items-center mb-10"><div className="brand"><AudioLines size={25} /><span>Le Closer<span className="brand-period">.</span></span></div><div className="flex gap-3"><button onClick={onBack} className="secondary-button">View call workspace</button><button onClick={onNewCall} className="primary-button">Set up another call</button></div></header>
      <div className="mb-8"><span className="eyebrow">CALL REVIEW</span><h1 className="text-3xl font-semibold tracking-tight mt-3">Keep the conversation moving.</h1><p className="mt-3 text-muted">{call.client.company} <span className="mx-2">·</span> Review your notes and next steps.</p></div>
      <div className="post-grid">
        <div className="space-y-5">
          <section className="post-section"><div className="panel-heading"><div className="flex gap-2 items-center"><FileText size={18} className="text-muted" /><h2>Call summary</h2></div>{!call.notes && <Loader2 size={16} className="animate-spin text-accent" />}</div><div className="p-5 text-sm text-copy leading-relaxed whitespace-pre-wrap">{call.notes?.markdown || "Your call notes are being prepared. They’ll appear here when ready."}</div></section>
          <section className="post-section"><div className="panel-heading"><div className="flex gap-2 items-center"><ListChecks size={18} className="text-muted" /><h2>Action items</h2></div><span className="text-xs text-muted">{call.tasks.length} captured</span></div><ul className="p-5 space-y-4 text-sm">{call.tasks.length === 0 && <li className="text-muted">No action items were captured during this call.</li>}{call.tasks.map((t) => <li key={t.id} className="flex items-start gap-3"><CheckCircle2 size={17} className={`shrink-0 mt-0.5 ${t.status === "done" ? "text-success" : "text-muted"}`} /><div><p>{t.title}</p><p className="text-xs text-muted mt-1 capitalize">{t.owner} · {t.status}</p></div></li>)}</ul></section>
        </div>
        <section className="post-section"><div className="panel-heading"><div className="flex items-center gap-2"><Mail size={18} className="text-accent" /><h2>Follow-up email</h2></div></div><div className="p-5"><p role="status" className={`text-sm mb-4 ${call.followup_status === "sent" ? "text-success" : "text-accent"}`}>{STATUS[call.followup_status] || call.followup_status}</p><div className="bg-ink rounded-lg p-4 text-sm leading-relaxed whitespace-pre-wrap border border-line">{call.followup_draft || "Your follow-up draft is being prepared. You can review it here before sending."}</div>{call.followup_status === "awaiting_approval" && <><p className="text-xs text-muted mt-4 leading-relaxed">Review the draft above. Approving sends this email to your client.</p><div className="flex flex-wrap gap-3 mt-4"><button disabled={busy} onClick={() => decide("approve")} className="primary-button">{busy && <Loader2 size={16} className="animate-spin" />}Approve & send</button><button disabled={busy} onClick={() => decide("reject")} className="secondary-button">Reject draft</button></div></>}{error && <p role="alert" className="text-sm text-danger mt-4">{error}</p>}</div></section>
      </div>
    </div></main>
  );
}
