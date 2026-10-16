import React from "react";
import { Plus, ShieldCheck, MapPin, Landmark, X } from "lucide-react";
import { BELUR_ATTRACTIONS, UI_STRINGS } from "@/theme/tokens";

interface SidebarProps {
  language: "kn" | "en";
  onNewSession: () => void;
  onSelectAttraction: (query: string) => void;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  language,
  onNewSession,
  onSelectAttraction,
  onCloseMobile,
}) => {
  const t = UI_STRINGS[language];

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col h-full bg-heritage-sandstone/70 dark:bg-heritage-carved-basalt/60 border-r border-heritage-brown/10 dark:border-heritage-gold/15 p-4 overflow-y-auto">
      {/* Mobile close button */}
      <div className="flex md:hidden items-center justify-between pb-3 mb-2 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <span className="font-semibold text-sm text-heritage-brown dark:text-heritage-marble">
          {t.siteTitle}
        </span>
        <button
          onClick={onCloseMobile}
          aria-label="Close sidebar"
          className="p-1 rounded text-heritage-umber dark:text-heritage-stone hover:bg-heritage-ivory dark:hover:bg-heritage-deep-stone"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* New Session Button */}
      <button
        onClick={() => {
          onNewSession();
          onCloseMobile?.();
        }}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md font-medium text-sm bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-brown shadow-sm transition-all focus:ring-2 focus:ring-heritage-brown dark:focus:ring-heritage-gold active:scale-[0.98]"
      >
        <Plus className="w-4 h-4" />
        <span>{t.newSession}</span>
      </button>

      {/* Verified Grounding Guarantee Card */}
      <div className="mt-4 p-3 rounded-lg bg-heritage-ivory dark:bg-heritage-deep-stone border border-heritage-brown/10 dark:border-heritage-gold/15 shadow-sm">
        <div className="flex items-center gap-2 text-heritage-forest dark:text-emerald-400 font-semibold text-xs mb-1">
          <ShieldCheck className="w-4 h-4 flex-shrink-0" />
          <span>{t.groundedBadge}</span>
        </div>
        <p className="text-[11px] leading-relaxed text-heritage-umber dark:text-heritage-stone">
          {t.unsupportedNotice}
        </p>
      </div>

      {/* Temple Attractions List */}
      <div className="mt-6 flex-1">
        <h2 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone px-1 mb-3 flex items-center gap-1.5">
          <Landmark className="w-3.5 h-3.5 text-heritage-gold" />
          <span>{t.attractionsTitle}</span>
        </h2>

        <div className="space-y-2">
          {BELUR_ATTRACTIONS.map((attraction) => {
            const name = language === "kn" ? attraction.nameKn : attraction.nameEn;
            const desc = language === "kn" ? attraction.descriptionKn : attraction.descriptionEn;

            return (
              <button
                key={attraction.id}
                onClick={() => {
                  onSelectAttraction(name);
                  onCloseMobile?.();
                }}
                className="w-full text-left p-2.5 rounded-lg bg-heritage-ivory/80 dark:bg-heritage-deep-stone/80 hover:bg-heritage-ivory dark:hover:bg-heritage-deep-stone border border-transparent hover:border-heritage-gold/50 transition-all group focus:ring-2 focus:ring-heritage-gold"
              >
                <div className="flex items-start gap-2">
                  <MapPin className="w-3.5 h-3.5 text-heritage-gold mt-0.5 flex-shrink-0 group-hover:scale-110 transition-transform" />
                  <div>
                    <h3 className="text-xs font-semibold text-heritage-brown dark:text-heritage-marble group-hover:text-heritage-gold transition-colors line-clamp-1">
                      {name}
                    </h3>
                    <p className="text-[11px] text-heritage-umber dark:text-heritage-stone line-clamp-2 mt-0.5 leading-snug">
                      {desc}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-6 pt-3 border-t border-heritage-brown/10 dark:border-heritage-gold/15 text-[10px] text-center text-heritage-umber dark:text-heritage-stone">
        <span>Karnataka Tourism • Hoysala Architecture</span>
      </div>
    </aside>
  );
};
