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
  onSend: (text: string) => void;
}

export function WizardView({
  messages,
  streamingText,
  isStreaming,
  currentIndex,
  totalSteps,
  stepLabel,
  onSend,
}: WizardViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming tokens
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  return (
    <div className="flex flex-col gap-4 w-full max-w-3xl mx-auto">
      <WizardProgressDots currentIndex={currentIndex} />

      <WizardCard stepLabel={stepLabel} stepNumber={currentIndex} totalSteps={totalSteps}>
        {/* Scrollable conversation area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
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

        {/* Input */}
        <ChatInput onSend={onSend} disabled={isStreaming} />
      </WizardCard>
    </div>
  );
}
