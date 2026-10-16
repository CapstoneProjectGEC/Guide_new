import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { VoiceWidget } from "@/features/voice/VoiceWidget";
import { UI_STRINGS } from "@/theme/tokens";

interface MessageInputProps {
  language: "kn" | "en";
  isStreaming: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  onSendMessage: (content: string, inputMode: "text" | "voice") => void;
  onAudioRecorded: (blob: Blob) => void;
  onError: (msg: string) => void;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  language,
  isStreaming,
  isProcessing,
  isSpeaking,
  onSendMessage,
  onAudioRecorded,
  onError,
}) => {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const t = UI_STRINGS[language];

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isStreaming || isProcessing) return;

    onSendMessage(trimmed, "text");
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isDisabled = isStreaming || isProcessing;

  return (
    <div className="p-3 sm:p-4 bg-heritage-ivory/95 dark:bg-heritage-basalt/95 backdrop-blur-md border-t border-heritage-brown/10 dark:border-heritage-gold/15">
      <form
        onSubmit={handleSubmit}
        className="max-w-3xl mx-auto flex items-end gap-2 bg-heritage-sandstone dark:bg-heritage-deep-stone rounded-2xl p-2 border border-heritage-brown/15 dark:border-heritage-gold/25 shadow-sm focus-within:border-heritage-gold focus-within:ring-2 focus-within:ring-heritage-gold/30 transition-all"
      >
        {/* Voice Trigger */}
        <div className="flex-shrink-0 pb-1 pl-1">
          <VoiceWidget
            language={language}
            isProcessing={isProcessing}
            isSpeaking={isSpeaking}
            onAudioRecorded={onAudioRecorded}
            onError={onError}
          />
        </div>

        {/* Text Input Area (Supports Kannada Unicode) */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          rows={1}
          maxLength={2000}
          placeholder={t.askPlaceholder}
          aria-label="Ask the heritage guide a question"
          className="flex-1 max-h-32 bg-transparent text-sm text-heritage-brown dark:text-heritage-marble placeholder:text-heritage-umber/70 dark:placeholder:text-heritage-stone/70 resize-none outline-none py-2 px-1 font-sans leading-relaxed disabled:opacity-50"
        />

        {/* Send Button */}
        <button
          type="submit"
          disabled={!text.trim() || isDisabled}
          aria-label={t.askButton}
          className="flex-shrink-0 p-2.5 rounded-xl bg-heritage-gold text-heritage-brown font-semibold hover:bg-heritage-gold-radiant disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-all focus:ring-2 focus:ring-heritage-gold active:scale-95 mb-0.5"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      <div className="max-w-3xl mx-auto flex items-center justify-between text-[11px] text-heritage-umber dark:text-heritage-stone mt-1.5 px-2">
        <span>Press <kbd className="font-mono bg-heritage-sandstone dark:bg-heritage-deep-stone px-1 py-0.5 rounded border border-heritage-brown/10 dark:border-heritage-gold/20">Enter ↵</kbd> to send, <kbd className="font-mono bg-heritage-sandstone dark:bg-heritage-deep-stone px-1 py-0.5 rounded border border-heritage-brown/10 dark:border-heritage-gold/20">Shift+Enter</kbd> for newline</span>
        {text.length > 100 && (
          <span className="font-mono">{text.length}/2000</span>
        )}
      </div>
    </div>
  );
};
