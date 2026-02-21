import React, { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import gsap from "gsap";

interface AgentMessageProps {
  content: string;
  isStreaming?: boolean;
}

export function AgentMessage({ content, isStreaming = false }: AgentMessageProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      gsap.fromTo(ref.current, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" });
    }
  }, []);

  return (
    <div ref={ref} className="flex items-start gap-3 max-w-[85%]">
      <div className="w-8 h-8 rounded-full bg-canopy text-linen flex items-center justify-center shrink-0">
        <Bot size={16} />
      </div>
      <div className="bg-mist/30 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-slate">
        {content}
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-ember align-middle ml-1 animate-pulse" />
        )}
      </div>
    </div>
  );
}
