import React, { useEffect, useRef } from "react";
import type { ConversationMessage } from "../types";
import { WizardProgressDots } from "../components/WizardProgressDots";
import { WizardCard } from "../components/WizardCard";
import { AgentMessage } from "../components/AgentMessage";
import { UserMessage } from "../components/UserMessage";
import { ChatInput } from "../components/ChatInput";

interface WizardViewProps {
  messages: ConversationMessage[];
  streamingText: string;
  isStreaming: boolean;
  currentIndex: number;
  totalSteps: number;
  stepLabel: string;
  suggestions: string[];
  onSend: (text: string) => void;
}

export function WizardView({
  messages,
  streamingText,
  isStreaming,
  currentIndex,
  totalSteps,
  stepLabel,
  suggestions,
  onSend,
}: WizardViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming tokens
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText, suggestions]);

  return (
    <div className="flex flex-col gap-4 w-full">
      <WizardProgressDots currentIndex={currentIndex} />

      <WizardCard stepLabel={stepLabel} stepNumber={currentIndex} totalSteps={totalSteps}>
        {/* Scrollable conversation area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4 min-h-0">
          {messages.map((msg, i) =>
            msg.role === "assistant" ? (
              <AgentMessage key={i} content={msg.content} />
            ) : (
              <UserMessage key={i} content={msg.content} />
            ),
          )}
          {/* Currently streaming agent response */}
          {isStreaming && streamingText && (
            <AgentMessage content={streamingText} isStreaming />
          )}
          {/* Streaming but no tokens yet */}
          {isStreaming && !streamingText && (
            <AgentMessage content="" isStreaming />
          )}
        </div>

        {/* Quick-reply suggestion chips */}
        {!isStreaming && suggestions.length > 0 && (
          <div className="px-6 pb-3 pt-1 flex flex-wrap gap-2 border-t border-mist/50">
            {suggestions.map((suggestion, i) => (
              <button
                key={i}
                onClick={() => onSend(suggestion)}
                className="
                  px-3 py-1.5 rounded-full text-xs font-medium border border-canopy/30
                  bg-canopy/5 text-canopy hover:bg-canopy/15 hover:border-canopy/60
                  transition-all duration-150 cursor-pointer
                  animate-in fade-in slide-in-from-bottom-1
                "
                style={{ animationDelay: `${i * 60}ms`, animationFillMode: "both" }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <ChatInput onSend={onSend} disabled={isStreaming} />
      </WizardCard>
    </div>
  );
}
