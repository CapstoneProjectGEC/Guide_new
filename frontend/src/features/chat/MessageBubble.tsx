import React, { useState } from "react";
import {
  Copy,
  Check,
  Volume2,
  ShieldCheck,
  Clock,
  AlertCircle,
  AlertTriangle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";
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
  const [showSources, setShowSources] = useState(false);
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

        {/* Timings Uncertainty Alert Notice */}
        {message.has_timing_uncertainty && (
          <div className="mt-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Timings Inconsistency Note:</span> Published sources differ on whether the temple closes from 1:30 PM to 4:00 PM for rituals/cleaning or remains open continuously under ASI rules. Visitors are advised to confirm locally on arrival.
            </div>
          </div>
        )}

        {/* Inline Image Cards with Attribution & Hedges */}
        {message.images && message.images.length > 0 && (
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {message.images.map((img) => (
              <div
                key={img.image_id}
                className="rounded-xl overflow-hidden border border-heritage-gold/25 bg-heritage-sandstone/30 dark:bg-heritage-carved-basalt/60 shadow-sm flex flex-col"
              >
                {img.display_url && (
                  <div className="relative aspect-video bg-black/10 overflow-hidden">
                    <img
                      src={img.display_url}
                      alt={img.caption || img.image_id}
                      className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                    <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono bg-black/75 text-white font-semibold">
                      {img.image_id}
                    </span>
                  </div>
                )}
                <div className="p-2.5 flex-1 flex flex-col justify-between text-xs">
                  {img.caption && (
                    <p className={`text-heritage-brown dark:text-heritage-marble font-medium leading-snug mb-1.5 ${img.uncertain_caption ? "italic text-amber-700 dark:text-amber-300" : ""}`}>
                      {img.caption}
                    </p>
                  )}
                  <div className="pt-1.5 border-t border-heritage-brown/10 dark:border-heritage-gold/15 flex items-center justify-between text-[11px] text-heritage-umber dark:text-heritage-stone">
                    <span className="font-semibold">{img.source_site}</span>
                    {img.source_page_url && (
                      <a
                        href={img.source_page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-heritage-gold hover:underline"
                      >
                        Source Page <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Expandable Sources Accordion & Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-heritage-brown/10 dark:border-heritage-gold/15">
            <button
              onClick={() => setShowSources(!showSources)}
              className="w-full flex items-center justify-between text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold transition-colors py-1"
            >
              <span className="flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-heritage-gold" />
                Attributed Sources & Citations ({message.citations.length})
              </span>
              {showSources ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showSources ? (
              <div className="mt-2 space-y-2 animate-in fade-in duration-150">
                {message.citations.map((c, i) => (
                  <div
                    key={`${c.chunk_id}-${i}`}
                    className="p-2.5 rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/50 border border-heritage-brown/10 dark:border-heritage-gold/15 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold font-mono text-heritage-gold text-[11px]">
                        {c.section_id || c.chunk_id}
                      </span>
                      {c.source_url && (
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-heritage-gold hover:underline"
                        >
                          Source Link <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                    {c.source_page_title && (
                      <div className="text-[11px] font-medium text-heritage-brown dark:text-heritage-marble mt-0.5">
                        {c.source_page_title}
                      </div>
                    )}
                    {c.section_heading && (
                      <div className="text-[10px] text-heritage-umber dark:text-heritage-stone mt-0.5">
                        Section: {c.section_heading}
                      </div>
                    )}
                    <button
                      onClick={() => onCitationClick(c)}
                      className="mt-1.5 text-[10px] text-heritage-gold hover:underline font-semibold flex items-center gap-1"
                    >
                      View verbatim excerpt &rarr;
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {message.citations.map((c, i) => (
                  <CitationBadge
                    key={`${c.chunk_id}-${i}`}
                    citation={c}
                    index={i}
                    onClick={onCitationClick}
                  />
                ))}
              </div>
            )}
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
