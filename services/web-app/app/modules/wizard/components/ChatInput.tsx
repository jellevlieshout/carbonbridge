import React, { useState, useRef, useCallback } from "react";
import { Send } from "lucide-react";
import { cn } from "~/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="flex items-end gap-3 p-4 border-t border-mist bg-white/50">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder={disabled ? "Agent is thinking..." : "Type your message..."}
        rows={1}
        className={cn(
          "flex-1 resize-none rounded-xl border border-mist bg-white px-4 py-3 text-sm text-slate",
          "placeholder:text-slate/40 focus:outline-none focus:ring-2 focus:ring-canopy/20 focus:border-canopy/40",
          "transition-colors duration-200",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className={cn(
          "magnetic-btn w-10 h-10 rounded-full flex items-center justify-center shrink-0",
          "bg-canopy text-linen transition-all duration-200",
          disabled || !value.trim() ? "opacity-30 cursor-not-allowed" : "hover:bg-sage cursor-pointer",
        )}
      >
        <Send size={16} />
      </button>
    </div>
  );
}
