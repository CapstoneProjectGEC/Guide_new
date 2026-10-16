import React, { useEffect, useState } from "react";
import { X, Database, Globe, AlertTriangle, ExternalLink, Calendar, Layers, ShieldCheck } from "lucide-react";
import { KbInfo } from "@/types/api";

interface AboutKbModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutKbModal: React.FC<AboutKbModalProps> = ({ isOpen, onClose }) => {
  const [info, setInfo] = useState<KbInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!isOpen) return;

    fetch("/api/v1/chat/kb/info")
      .then((res) => res.json())
      .then((data: KbInfo) => {
        setInfo(data);
        setLoading(false);
      })
      .catch((err) => {
        console.warn("Could not fetch KB info:", err);
        setLoading(false);
      });
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="about-kb-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-heritage-ivory dark:bg-heritage-carved-basalt rounded-2xl shadow-2xl border border-heritage-gold/30 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-heritage-brown/10 dark:border-heritage-gold/20 flex items-center justify-between bg-heritage-sandstone/30 dark:bg-heritage-deep-stone/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-heritage-gold/20 text-heritage-brown dark:text-heritage-gold">
              <Database className="w-5 h-5 text-heritage-gold" />
            </div>
            <div>
              <h2 id="about-kb-title" className="text-base font-bold font-display text-heritage-brown dark:text-heritage-marble">
                About This Guide's Knowledge Base
              </h2>
              <p className="text-xs text-heritage-umber dark:text-heritage-stone font-mono">
                BELUR-KB-001 v1.0 • Offline RAG Grounding Engine
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close knowledge base details"
            className="p-1.5 rounded-lg text-heritage-umber dark:text-heritage-stone hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone hover:text-heritage-brown dark:hover:text-heritage-marble transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-5 text-sm font-sans">
          {/* Metadata Badges Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="p-3 rounded-xl bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15">
              <div className="text-[10px] text-heritage-umber dark:text-heritage-stone flex items-center gap-1 uppercase font-semibold">
                <Layers className="w-3 h-3 text-heritage-gold" /> Version
              </div>
              <div className="text-xs font-bold font-mono text-heritage-brown dark:text-heritage-marble mt-1">
                {info?.kb_version || "BELUR-KB-001 v1.0"}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15">
              <div className="text-[10px] text-heritage-umber dark:text-heritage-stone flex items-center gap-1 uppercase font-semibold">
                <Calendar className="w-3 h-3 text-heritage-gold" /> Extracted
              </div>
              <div className="text-xs font-bold font-mono text-heritage-brown dark:text-heritage-marble mt-1">
                {info?.extraction_date || "2026-10-16"}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15">
              <div className="text-[10px] text-heritage-umber dark:text-heritage-stone flex items-center gap-1 uppercase font-semibold">
                <ShieldCheck className="w-3 h-3 text-emerald-500" /> Grounding
              </div>
              <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                100% Strict Offline
              </div>
            </div>

            <div className="p-3 rounded-xl bg-heritage-sandstone/50 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15">
              <div className="text-[10px] text-heritage-umber dark:text-heritage-stone flex items-center gap-1 uppercase font-semibold">
                <Database className="w-3 h-3 text-heritage-gold" /> Chunks
              </div>
              <div className="text-xs font-bold font-mono text-heritage-brown dark:text-heritage-marble mt-1">
                {info?.total_chunks || 86} indexed
              </div>
            </div>
          </div>

          {/* Sources Section */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone mb-2 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-heritage-gold" />
              Processed Primary Source Pages ({info?.source_pages?.length || 6})
            </h3>
            <div className="space-y-2">
              {info?.source_pages?.map((src, i) => (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-white dark:bg-heritage-deep-stone/60 border border-heritage-brown/10 dark:border-heritage-gold/15 flex items-start justify-between gap-3"
                >
                  <div>
                    <div className="font-semibold text-xs text-heritage-brown dark:text-heritage-marble">
                      {src.title}
                    </div>
                    <div className="text-[11px] text-heritage-umber dark:text-heritage-stone font-mono mt-0.5">
                      {src.site} • {src.content_extracted}
                    </div>
                  </div>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 p-1 rounded text-heritage-gold hover:bg-heritage-gold/10 transition-colors"
                    title="View live website"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              ))}
            </div>
          </div>

          {/* Known Limitations and Gaps from extraction_report.md */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              Known Data Gaps & Transparency Notes (extraction_report.md)
            </h3>
            <div className="p-3.5 rounded-xl bg-amber-500/5 dark:bg-amber-500/10 border border-amber-500/20 text-xs text-heritage-brown dark:text-heritage-marble space-y-2 leading-relaxed">
              <p>
                <strong>1. Scoped Extraction:</strong> This knowledge base covers 6 in-scope Belur pages from ExploreKarnataka.com and Temples.bio. General blogs and unrelated monument pages were excluded.
              </p>
              <p>
                <strong>2. Third-Party Images:</strong> All 21 images are third-party photos catalogued from public pages. Usage permissions must be confirmed prior to public distribution. Captions marked as UNCERTAIN apply to group layouts.
              </p>
              <p>
                <strong>3. Timings Disagreement (C01):</strong> Sources disagree on midday closure (1:30 PM–4:00 PM vs continuous ASI hours). The guide preserves both accounts.
              </p>
              <p>
                <strong>4. Uninvented Legends:</strong> Local tales mentioned by name (e.g. Kappe Chennigaraya, Queen Shanthala's inscription text) are not narrated in source text and are never filled by model memory.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-heritage-brown/10 dark:border-heritage-gold/15 bg-heritage-sandstone/20 dark:bg-heritage-deep-stone/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-heritage-gold text-heritage-deep-stone hover:bg-heritage-gold/90 transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
