import { useEffect, useRef } from "react";
import { useCallStore, speakerLabel } from "../../store/callStore";

export default function Transcript() {
  const call = useCallStore((s) => s.call);
  const segments = call?.segments ?? [];
  const partials = useCallStore((s) => s.partials);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }); }, [segments.length, partials]);

  return (
    <div ref={ref} className="flex-1 overflow-y-auto space-y-4 text-sm p-4 leading-relaxed">
      {segments.length === 0 && Object.keys(partials).length === 0 && <div className="transcript-empty"><p className="text-slate-300 font-medium">{call?.ended ? "No transcript was captured" : "Your conversation will appear here"}</p><p className="text-slate-400 mt-2">{call?.ended ? "Audio wasn’t captured during this call." : call?.demo ? "Start the demo script to follow along." : "Share meeting audio above to start transcription."}</p></div>}
      {segments.map((s) => {
        const name = speakerLabel(call, s.speaker);
        const isRep = s.speaker === "rep";
        return (
          <p key={s.id} className={isRep ? "text-sky-300" : "text-amber-200"}>
            <b className="block text-xs mb-1 font-medium">{name}: </b>{s.text}
          </p>
        );
      })}
      {Object.entries(partials).map(([sp, text]) => (
        <p key={sp} className={`italic opacity-60 ${sp === "rep" ? "text-sky-300" : "text-amber-200"}`}>
          <b className="block text-xs mb-1">{speakerLabel(call, sp)}: </b>{text}▌
        </p>
      ))}
    </div>
  );
}
