import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function RichText({ text, collapsible = false }: { text: string; collapsible?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  // Older calls may contain a stringified SDK object instead of a final answer.
  const content = /(?:ThinkChunk|TextChunk)\s*\(/.test(text)
    ? "This older answer could not be displayed. Ask copilot again for a clean answer."
    : text;
  const canCollapse = collapsible && content.length > 1000;
  return <div>
    <div className={`rich-text ${canCollapse && !expanded ? "rich-text-collapsed" : ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={{
        a: ({ children, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>,
        img: () => null,
        table: ({ children, ...props }) => <div className="rich-table"><table {...props}>{children}</table></div>,
      }}>{content}</ReactMarkdown>
    </div>
    {canCollapse && <button type="button" className="rich-text-toggle" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Show less" : "Show full answer"}</button>}
  </div>;
}
