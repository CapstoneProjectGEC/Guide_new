import React, { useState } from "react";
import { Copy, Check, Volume2, ShieldCheck, Clock, AlertCircle } from "lucide-react";
import { ChatMessage, Citation } from "@/types/api";
import { CitationBadge } from "./CitationBadge";
import { UI_STRINGS } from "@/theme/tokens";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
  language: "kn" | "en";
  onCitationClick: (citation: Citation) => void;
  onSpeakMessage?: (text: string, language: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isStreaming,
  language,
  onCitationClick,
  onSpeakMessage,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";
  const t = UI_STRINGS[language];

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4 animate-in fade-in slide-in-from-bottom-2 duration-150">
        <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-tr-sm bg-heritage-gold/20 dark:bg-heritage-gold/15 text-heritage-brown dark:text-heritage-marble px-4 py-3 border border-heritage-gold/30 shadow-sm">
          <p className="text-sm font-sans leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </p>
          <div className="flex justify-end items-center gap-1.5 mt-1.5 text-[10px] text-heritage-umber dark:text-heritage-stone font-mono">
            <span>{message.input_mode === "voice" ? "🎤 Voice" : "⌨ Text"}</span>
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="flex justify-start mb-5 animate-in fade-in slide-in-from-bottom-2 duration-150">
      <div className="max-w-[95%] sm:max-w-[85%] rounded-2xl rounded-tl-sm bg-heritage-ivory dark:bg-heritage-deep-stone text-heritage-brown dark:text-heritage-marble px-4 sm:px-5 py-4 border-l-4 border-heritage-gold border-t border-r border-b border-heritage-brown/10 dark:border-heritage-gold/15 shadow-sm">
        {/* Assistant Header Tag */}
        <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-heritage-brown/10 dark:border-heritage-gold/15 text-xs">
          <div className="flex items-center gap-1.5">
            <span role="img" aria-label="Hoysala Guide" className="text-sm select-none">
              🛕
            </span>
            <span className="font-bold font-display text-heritage-brown dark:text-heritage-marble">
              Belur Heritage Guide
            </span>
            {message.is_grounded ? (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="w-3 h-3" />
                Verified
              </span>
            ) : (
              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <AlertCircle className="w-3 h-3" />
                Fallback
              </span>
            )}
          </div>

          {message.latency_ms && (
            <span className="text-[10px] text-heritage-umber dark:text-heritage-stone font-mono flex items-center gap-0.5">
              <Clock className="w-3 h-3" />
              {message.latency_ms}ms
            </span>
          )}
        </div>

        {/* Content Body */}
        <div className="text-sm font-sans leading-relaxed whitespace-pre-wrap break-words text-heritage-brown dark:text-heritage-marble">
          {message.content}
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-heritage-gold ml-1 animate-pulse align-middle" />
          )}
        </div>

        {/* Citations Badges */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-heritage-brown/10 dark:border-heritage-gold/15">
            <div className="text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1.5">
              Attributed Sources:
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, i) => (
                <CitationBadge
                  key={`${c.chunk_id}-${i}`}
                  citation={c}
                  index={i}
                  onClick={onCitationClick}
                />
              ))}
            </div>
          </div>
        )}

        {/* Action Controls (Listen, Copy) */}
        {!isStreaming && (
          <div className="mt-3 pt-2 flex items-center justify-between text-xs text-heritage-umber dark:text-heritage-stone border-t border-heritage-brown/5 dark:border-heritage-gold/10">
            <div className="flex items-center gap-2">
              {onSpeakMessage && (
                <button
                  onClick={() => onSpeakMessage(message.content, message.detected_language || language)}
                  aria-label="Listen to answer with speech synthesis"
                  className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:text-heritage-gold transition-colors focus:ring-1 focus:ring-heritage-gold"
                >
                  <Volume2 className="w-3.5 h-3.5 text-heritage-gold" />
                  <span>{t.speakAnswer}</span>
                </button>
              )}

              <button
                onClick={handleCopy}
                aria-label="Copy answer to clipboard"
                className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:text-heritage-gold transition-colors focus:ring-1 focus:ring-heritage-gold"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>{t.copyAnswer}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
