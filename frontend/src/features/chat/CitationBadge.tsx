import React from "react";
import { BookOpen } from "lucide-react";
import { Citation } from "@/types/api";
import { UI_STRINGS } from "@/theme/tokens";

interface CitationBadgeProps {
  citation: Citation;
  index: number;
  language?: "kn" | "en";
  onClick: (citation: Citation) => void;
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({
  citation,
  index,
  language = "en",
  onClick,
}) => {
  const t = UI_STRINGS[language] || UI_STRINGS.en;
  return (
    <button
      onClick={() => onClick(citation)}
      aria-label={`View citation source: ${citation.document_id}, page ${citation.page_number}`}
      title={`${t.source}: ${citation.document_id} (Page ${citation.page_number}) - Click to inspect`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-heritage-sandstone dark:bg-heritage-deep-stone text-heritage-brown dark:text-heritage-gold border border-heritage-gold/30 hover:border-heritage-gold hover:bg-heritage-gold/15 transition-all shadow-xs focus:ring-1 focus:ring-heritage-gold active:scale-95"
    >
      <BookOpen className="w-3 h-3 text-heritage-gold flex-shrink-0" />
      <span>
        {t.source} [{index + 1}: p.{citation.page_number}]
      </span>
    </button>
  );
};
