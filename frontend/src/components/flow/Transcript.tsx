import { useEffect, useRef } from "react";
import { useCallStore, speakerLabel } from "../../store/callStore";

export default function Transcript() {
  const call = useCallStore((s) => s.call);
  const segments = call?.segments ?? [];
  const partials = useCallStore((s) => s.partials);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ top: ref.current.scrollHeight }); }, [segments.length, partials]);

  return (
    <div ref={ref} className="flex-1 overflow-y-auto space-y-1.5 text-sm pr-1">
      {segments.map((s) => {
        const name = speakerLabel(call, s.speaker);
        const isRep = s.speaker === "rep";
        return (
          <p key={s.id} className={isRep ? "text-sky-300" : "text-amber-200"}>
            <b className="text-[10px] uppercase opacity-80">{name}: </b>{s.text}
          </p>
        );
      })}
      {Object.entries(partials).map(([sp, text]) => (
        <p key={sp} className={`italic opacity-60 ${sp === "rep" ? "text-sky-300" : "text-amber-200"}`}>
          <b className="text-[10px] uppercase">{speakerLabel(call, sp)}: </b>{text}▌
        </p>
      ))}
    </div>
  );
}
