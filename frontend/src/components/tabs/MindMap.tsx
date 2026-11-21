import { useEffect, useMemo, useRef, useState } from "react";
import { Download, Focus, GitBranch, ListTree, Minus, Plus } from "lucide-react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { useCallStore } from "../../store/callStore";

const transformer = new Transformer();

export default function MindMap() {
  const md = useCallStore((s) => s.call?.mindmap_md ?? "# Call");
  const ended = useCallStore((s) => s.call?.ended);
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const mmRef = useRef<Markmap | null>(null);
  const firstRender = useRef(true);
  const [view, setView] = useState<"map" | "outline">("map");
  const [details, setDetails] = useState(false);
  const previousDetails = useRef(false);
  const [autoFit, setAutoFit] = useState(false);
  const [error, setError] = useState("");
  const { root } = useMemo(() => transformer.transform(md), [md]);
  const hasContent = (root.children?.length ?? 0) > 0;
  const branches = root.children?.length ?? 0;

  useEffect(() => {
    if (view !== "map" || !hasContent || !svgRef.current) return;
    const map = Markmap.create(svgRef.current, {
      duration: 0, maxInitialScale: 1.4, scrollForPan: false, maxWidth: 220, spacingHorizontal: 60, spacingVertical: 16,
      paddingX: 12, color: () => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(),
    });
    mmRef.current = map;
    firstRender.current = true;
    // Hidden workspace tabs may have no dimensions until selected.
    const observer = new ResizeObserver((entries) => {
      if (entries[0]?.contentRect.width && entries[0]?.contentRect.height && map.state.data) void map.fit();
    });
    if (canvasRef.current) observer.observe(canvasRef.current);
    return () => { observer.disconnect(); map.destroy(); mmRef.current = null; };
  }, [view, hasContent]);

  useEffect(() => {
    const map = mmRef.current;
    if (!map) return;
    let cancelled = false;
    setError("");
    const changedDetail = details !== previousDetails.current;
    const data = structuredClone(root);
    const previousBranches = map.state.data?.children ?? [];
    for (const branch of data.children ?? []) {
      const previous = previousBranches.find((node) => node.content === branch.content);
      branch.payload = { ...branch.payload, fold: changedDetail ? (details ? 0 : 1) : previous ? (previous.payload?.fold ?? 0) : (details ? 0 : 1) };
    }
    previousDetails.current = details;
    void map.setData(data).then(async () => {
      if (cancelled) return;
      if (firstRender.current || autoFit || changedDetail) await map.fit();
      firstRender.current = false;
    }).catch(() => { if (!cancelled) setError("The map couldn’t be rendered. Switch to Outline to read the call notes."); });
    return () => { cancelled = true; };
  }, [root, view, autoFit, hasContent, details]);

  const zoom = (scale: number) => { setAutoFit(false); void mmRef.current?.rescale(scale); };
  const download = () => {
    const url = URL.createObjectURL(new Blob([md], { type: "text/markdown;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = "call-mind-map.md"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const outline = md.split("\n").filter((line) => line.trim() && !line.startsWith("```"));
  return (
    <div className="mindmap-tool">
      <div className="tool-toolbar">
        <div className="tool-switch" role="group" aria-label="Mind map view">
          <button aria-pressed={view === "map"} onClick={() => setView("map")}><GitBranch size={15} /> Map</button>
          <button aria-pressed={view === "outline"} onClick={() => setView("outline")}><ListTree size={15} /> Outline</button>
        </div>
        <button className="tool-icon-button" onClick={download} disabled={!hasContent} aria-label="Download mind map as Markdown" title="Download Markdown"><Download size={17} /></button>
      </div>
      {!hasContent ? <div className="tool-empty"><GitBranch size={30} /><h3>{ended ? "No topics captured" : "See the conversation take shape"}</h3><p>{ended ? "This call has no mind map to review." : "Client needs, objections, people, and next steps will become connected branches as you talk."}</p><span>Switch to Outline anytime for a text view.</span></div>
        : view === "outline" ? <div className="mindmap-outline" aria-label="Call topic outline">{outline.map((line, i) => {
          const heading = /^(#{1,6})\s+/.exec(line);
          const indent = heading ? Math.max(0, heading[1].length - 2) : Math.floor((/^\s*/.exec(line)?.[0].length ?? 0) / 2) + 1;
          return <div key={i} className={heading ? "outline-heading" : "outline-item"} style={{ paddingLeft: `${Math.min(indent, 5) * 16}px` }}>{line.replace(/^\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+)/, "")}</div>;
        })}</div>
        : <div className="mindmap-canvas" ref={canvasRef}>
          <svg ref={svgRef} role="img" aria-label="Interactive call mind map. Drag to pan, scroll to zoom, and click a branch circle to collapse it." />
          <div className="map-navigation" role="group" aria-label="Map navigation"><button onClick={() => zoom(1.25)} aria-label="Zoom in" title="Zoom in"><Plus size={17} /></button><button onClick={() => zoom(.8)} aria-label="Zoom out" title="Zoom out"><Minus size={17} /></button><button onClick={() => void mmRef.current?.fit()} aria-label="Fit mind map to view" title="Fit to view"><Focus size={17} /></button></div>
        </div>}
      {error && <p role="alert" className="text-sm text-danger mt-2">{error}</p>}
      {hasContent && <div className="tool-footer"><span>{branches} topic{branches === 1 ? "" : "s"}</span>{view === "map" && <button className="text-copy hover:text-accent" onClick={() => setDetails(!details)}>{details ? "Collapse all" : "Expand all"}</button>}{view === "map" && <label><input type="checkbox" checked={autoFit} onChange={(e) => setAutoFit(e.target.checked)} /> Auto-fit updates</label>}</div>}
      {hasContent && view === "map" && <p className="map-hint">Drag to explore · Scroll to zoom · Click circles to fold branches</p>}
    </div>
  );
}
