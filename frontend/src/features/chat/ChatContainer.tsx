import React, { useRef, useEffect } from "react";
import { ShieldCheck } from "lucide-react";
import { ChatMessage, Citation } from "@/types/api";
import { MessageBubble } from "./MessageBubble";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { UI_STRINGS } from "@/theme/tokens";

interface ChatContainerProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  language: "kn" | "en";
  onSelectSuggestedQuestion: (text: string) => void;
  onCitationClick: (citation: Citation) => void;
  onSpeakMessage?: (text: string, language: string) => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isStreaming,
  streamingMessageId,
  language,
  onSelectSuggestedQuestion,
  onCitationClick,
  onSpeakMessage,
}) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const t = UI_STRINGS[language];

  // Auto-scroll to bottom on message change or streaming update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 max-w-3xl w-full mx-auto flex flex-col">
      {isEmpty ? (
        /* Empty Welcoming Guide Screen */
        <div className="my-auto py-8 text-center animate-in fade-in duration-300">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-heritage-gold/20 flex items-center justify-center text-3xl select-none shadow-sm border border-heritage-gold/30">
            🛕
          </div>

          <h2 className="text-xl sm:text-2xl font-bold font-display text-heritage-brown dark:text-heritage-marble tracking-tight">
            {t.monumentName}
          </h2>
          <p className="text-xs sm:text-sm text-heritage-gold font-semibold mt-1">
            {t.subtitle}
          </p>
          <p className="text-xs sm:text-sm text-heritage-umber dark:text-heritage-stone max-w-lg mx-auto mt-2 leading-relaxed">
            {t.tagline}
          </p>

          {/* Factual grounding assurance */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 mt-4 rounded-full bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-umber dark:text-heritage-stone text-xs border border-heritage-brown/10 dark:border-heritage-gold/15">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>{t.unsupportedNotice}</span>
          </div>

          {/* Curated Suggested Questions */}
          <SuggestedQuestions
            language={language}
            onSelectQuestion={onSelectSuggestedQuestion}
          />
        </div>
      ) : (
        /* Message Stream */
        <div className="flex-1 space-y-2">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isStreaming={isStreaming && msg.id === streamingMessageId}
              language={language}
              onCitationClick={onCitationClick}
              onSpeakMessage={onSpeakMessage}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};
