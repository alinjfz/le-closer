import { useCallStore } from "../../store/callStore";

export default function PrototypeFrame() {
  const prototypes = useCallStore((s) => s.call?.prototypes ?? []);
  const latest = prototypes[prototypes.length - 1];

  if (!latest) {
    return <div className="h-full flex items-center justify-center text-sm text-slate-500 text-center p-4">
      Prototypes built by Le Chonk appear here in a sandboxed iframe.<br />Click "Prototype ▶" on an integration card.
    </div>;
  }
  return (
    <iframe
      title={latest.title}
      sandbox="allow-scripts"
      srcDoc={latest.html}
      className="w-full h-full rounded-lg border border-slate-700 bg-white"
    />
  );
}
