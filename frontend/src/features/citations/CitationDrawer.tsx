import React from "react";
import { X, FileText, CheckCircle2, BookOpen } from "lucide-react";
import { Citation } from "@/types/api";
import { UI_STRINGS } from "@/theme/tokens";

interface CitationDrawerProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
  language: "kn" | "en";
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  citation,
  isOpen,
  onClose,
  language,
}) => {
  const t = UI_STRINGS[language];

  if (!isOpen || !citation) {
    return null;
  }

  const scorePct = Math.min(100, Math.round(citation.relevance_score * 100));

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="citation-title"
      className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-heritage-ivory dark:bg-heritage-carved-basalt shadow-2xl border-l border-heritage-brown/15 dark:border-heritage-gold/20 flex flex-col animate-in slide-in-from-right duration-200"
    >
      {/* Drawer Header */}
      <div className="p-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-heritage-gold" />
          <h2 id="citation-title" className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
            {t.citationsTitle}
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close citation details"
          className="p-1 rounded-md text-heritage-umber dark:text-heritage-stone hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Drawer Body */}
      <div className="p-4 overflow-y-auto flex-1 space-y-4">
        {/* Document Info Card */}
        <div className="p-3.5 rounded-lg bg-heritage-sandstone dark:bg-heritage-deep-stone border border-heritage-brown/10 dark:border-heritage-gold/15">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-heritage-brown dark:text-heritage-marble">
              <FileText className="w-4 h-4 text-heritage-gold" />
              <span>{citation.document_id}</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-heritage-gold/20 text-heritage-brown dark:text-heritage-gold border border-heritage-gold/30">
              {t.citationPage} {citation.page_number}
            </span>
          </div>

          {citation.section_heading && (
            <div className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
              <span className="font-semibold text-heritage-brown dark:text-heritage-marble">Section:</span>{" "}
              {citation.section_heading}
            </div>
          )}

          {/* Relevance Match Meter */}
          <div className="mt-3 pt-2.5 border-t border-heritage-brown/10 dark:border-heritage-gold/15 flex items-center justify-between text-xs">
            <span className="text-heritage-umber dark:text-heritage-stone flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              {t.relevance}:
            </span>
            <span className="font-mono font-bold text-heritage-forest dark:text-emerald-400">
              {scorePct}% Match
            </span>
          </div>
        </div>

        {/* Verbatim Excerpt */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone mb-1.5">
            Verbatim Knowledge Chunk Excerpt
          </h3>
          <div className="p-3.5 rounded-lg bg-white dark:bg-heritage-deep-stone/90 border border-heritage-brown/10 dark:border-heritage-gold/15 text-xs text-heritage-brown dark:text-heritage-marble leading-relaxed font-sans shadow-sm">
            "{citation.snippet}"
          </div>
        </div>

        {/* Metadata Badges */}
        <div className="text-[10px] text-heritage-umber dark:text-heritage-stone font-mono p-2.5 rounded bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/50">
          <div>Chunk ID: {citation.chunk_id}</div>
          <div className="mt-0.5">Grounding: Strict Hybrid RAG (Dense + BM25 + CrossEncoder)</div>
        </div>
      </div>

      {/* Drawer Footer */}
      <div className="p-3 border-t border-heritage-brown/10 dark:border-heritage-gold/15 bg-heritage-sandstone/50 dark:bg-heritage-carved-basalt text-center">
        <button
          onClick={onClose}
          className="w-full py-2 rounded-md text-xs font-medium bg-heritage-sandstone dark:bg-heritage-deep-stone text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors"
        >
          Close Drawer
        </button>
      </div>
    </div>
  );
};
