import { useEffect, useRef } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { useCallStore } from "../../store/callStore";

const transformer = new Transformer();

export default function MindMap() {
  const md = useCallStore((s) => s.call?.mindmap_md ?? "# Call");
  const svgRef = useRef<SVGSVGElement>(null);
  const mmRef = useRef<Markmap | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    if (!mmRef.current) mmRef.current = Markmap.create(svgRef.current);
    const { root } = transformer.transform(md);
    mmRef.current.setData(root);
    mmRef.current.fit();
  }, [md]);

  return (
    <div className="h-full bg-ink rounded-lg border border-slate-700 overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
