import React, { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import gsap from "gsap";

interface AgentMessageProps {
  content: string;
  isStreaming?: boolean;
}

/** Lightly format agent message text: bold **text**, line breaks */
function formatContent(text: string): React.ReactNode[] {
  if (!text) return [];
  const lines = text.split("\n");
  return lines.map((line, li) => {
    const parts: React.ReactNode[] = [];
    let remaining = line;
    let key = 0;
    while (remaining.length > 0) {
      const boldStart = remaining.indexOf("**");
      if (boldStart === -1) {
        parts.push(<span key={key++}>{remaining}</span>);
        break;
      }
      if (boldStart > 0) {
        parts.push(<span key={key++}>{remaining.slice(0, boldStart)}</span>);
      }
      const boldEnd = remaining.indexOf("**", boldStart + 2);
      if (boldEnd === -1) {
        parts.push(<span key={key++}>{remaining.slice(boldStart)}</span>);
        break;
      }
      parts.push(
        <strong key={key++} className="font-semibold text-slate">
          {remaining.slice(boldStart + 2, boldEnd)}
        </strong>,
      );
      remaining = remaining.slice(boldEnd + 2);
    }
    return (
      <React.Fragment key={li}>
        {parts}
        {li < lines.length - 1 && <br />}
      </React.Fragment>
    );
  });
}

export function AgentMessage({ content, isStreaming = false }: AgentMessageProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && !isStreaming) {
      gsap.fromTo(ref.current, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
    }
  }, [isStreaming]);

  return (
    <div ref={ref} className="flex items-start gap-3 max-w-[88%]">
      <div className="w-8 h-8 rounded-full bg-canopy text-linen flex items-center justify-center shrink-0 mt-0.5">
        <Bot size={15} />
      </div>
      <div className="bg-mist/40 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-slate shadow-sm">
        {content ? formatContent(content) : null}
        {isStreaming && (
          <span className="inline-block w-1.5 h-4 bg-canopy/60 align-middle ml-1 rounded-sm animate-pulse" />
        )}
      </div>
    </div>
  );
}
