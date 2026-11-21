import { useEffect, useRef, useState } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { useCallStore } from "../../store/callStore";

const transformer = new Transformer();

export default function MindMap() {
  const md = useCallStore((s) => s.call?.mindmap_md ?? "# Call");
  const svgRef = useRef<SVGSVGElement>(null);
  const mmRef = useRef<Markmap | null>(null);
  const [fontSize, setFontSize] = useState(11);

  useEffect(() => {
    if (!svgRef.current) return;
    if (!mmRef.current) mmRef.current = Markmap.create(svgRef.current);
    const { root } = transformer.transform(md);
    mmRef.current.setData(root);
    mmRef.current.fit();
  }, [md]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-1 shrink-0 text-[10px] text-slate-500">
        <span>font</span>
        <input type="range" min={7} max={20} value={fontSize}
          onChange={(e) => setFontSize(Number(e.target.value))}
          className="flex-1 accent-amber-500 h-1" />
        <span className="w-6 text-right">{fontSize}px</span>
      </div>
      <div className="flex-1 min-h-0 bg-ink rounded-lg border border-slate-700 overflow-hidden"
        style={{ ["--mm-fs" as any]: `${fontSize}px` }}>
        <style>{`.markmap-node text { font-size: var(--mm-fs) !important; font-weight: 400 !important; }`}</style>
        <svg ref={svgRef} className="w-full h-full" />
      </div>
    </div>
  );
}
