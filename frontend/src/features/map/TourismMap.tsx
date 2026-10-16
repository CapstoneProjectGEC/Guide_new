import React, { useState } from "react";
import { MapPin, X, Navigation, MessageSquare } from "lucide-react";
import { BELUR_ATTRACTIONS, TempleAttraction, UI_STRINGS } from "@/theme/tokens";

interface TourismMapProps {
  isOpen: boolean;
  onClose: () => void;
  language: "kn" | "en";
  onAskAboutAttraction: (query: string) => void;
}

export const TourismMap: React.FC<TourismMapProps> = ({
  isOpen,
  onClose,
  language,
  onAskAboutAttraction,
}) => {
  const [selectedAttraction, setSelectedAttraction] = useState<TempleAttraction>(BELUR_ATTRACTIONS[0]);
  const t = UI_STRINGS[language];

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="map-title"
      className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-heritage-ivory dark:bg-heritage-carved-basalt shadow-2xl border-l border-heritage-brown/15 dark:border-heritage-gold/20 flex flex-col animate-in slide-in-from-right duration-200"
    >
      {/* Header */}
      <div className="p-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Navigation className="w-5 h-5 text-heritage-gold" />
          <h2 id="map-title" className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
            {t.exploreMap} — Belur Heritage Precinct
          </h2>
        </div>
        <button
          onClick={onClose}
          aria-label="Close precinct map"
          className="p-1 rounded-md text-heritage-umber dark:text-heritage-stone hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Stylized Architectural Precinct Diagram */}
      <div className="p-4 bg-heritage-sandstone/60 dark:bg-heritage-deep-stone/80 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div className="relative w-full h-56 rounded-lg bg-heritage-ivory dark:bg-heritage-basalt border-2 border-heritage-gold/30 overflow-hidden shadow-inner flex items-center justify-center p-2">
          {/* Precinct Ground Pattern (Soapstone Star Layout) */}
          <div className="absolute inset-4 rounded-full border border-dashed border-heritage-gold/20 pointer-events-none" />
          <div className="absolute inset-12 rounded-lg rotate-45 border border-heritage-gold/25 pointer-events-none" />

          {/* Interactive Pins */}
          {BELUR_ATTRACTIONS.map((attraction, idx) => {
            const isSelected = selectedAttraction.id === attraction.id;
            // Coordinate relative positioning within diagram
            const positions = [
              { top: "45%", left: "48%" }, // Main Sanctum
              { top: "42%", left: "68%" }, // Navaranga
              { top: "25%", left: "45%" }, // Darpana Sundari
              { top: "68%", left: "30%" }, // Kappe Chennigraya
              { top: "20%", left: "80%" }, // Pushkarani
            ];
            const pos = positions[idx] || { top: "50%", left: "50%" };

            return (
              <button
                key={attraction.id}
                onClick={() => setSelectedAttraction(attraction)}
                style={{ top: pos.top, left: pos.left }}
                aria-label={attraction.nameEn}
                title={attraction.nameEn}
                className={`absolute -translate-x-1/2 -translate-y-1/2 p-2 rounded-full transition-all focus:outline-none focus:ring-2 focus:ring-heritage-gold ${
                  isSelected
                    ? "bg-heritage-gold text-heritage-brown scale-125 z-10 shadow-gold-glow"
                    : "bg-heritage-sandstone dark:bg-heritage-deep-stone text-heritage-gold hover:scale-110 shadow-sm"
                }`}
              >
                <MapPin className="w-4 h-4 fill-current" />
              </button>
            );
          })}

          {/* Compass Rose */}
          <div className="absolute top-2 right-2 text-[10px] font-mono font-bold text-heritage-umber dark:text-heritage-stone select-none bg-heritage-ivory/80 dark:bg-heritage-deep-stone/80 px-1.5 py-0.5 rounded border border-heritage-gold/20">
            N ↑
          </div>

          <div className="absolute bottom-2 left-2 text-[10px] text-heritage-umber dark:text-heritage-stone select-none">
            ★ Hoysala Star Platform (Jagati)
          </div>
        </div>
      </div>

      {/* Selected Monument Details */}
      <div className="p-4 overflow-y-auto flex-1 space-y-3">
        <div className="p-3.5 rounded-lg bg-heritage-sandstone dark:bg-heritage-deep-stone border border-heritage-brown/10 dark:border-heritage-gold/15">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[11px] font-bold text-heritage-gold uppercase tracking-wider">
              {selectedAttraction.highlight}
            </span>
            <span className="text-[10px] font-mono text-heritage-umber dark:text-heritage-stone">
              {selectedAttraction.lat.toFixed(4)}° N, {selectedAttraction.lng.toFixed(4)}° E
            </span>
          </div>

          <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble mb-2">
            {language === "kn" ? selectedAttraction.nameKn : selectedAttraction.nameEn}
          </h3>

          <p className="text-xs text-heritage-umber dark:text-heritage-stone leading-relaxed">
            {language === "kn" ? selectedAttraction.descriptionKn : selectedAttraction.descriptionEn}
          </p>

          <button
            onClick={() => {
              const query = language === "kn"
                ? `${selectedAttraction.nameKn} ಬಗ್ಗೆ ವಿವರವಾಗಿ ತಿಳಿಸಿ`
                : `Tell me about the ${selectedAttraction.nameEn} at Belur.`;
              onAskAboutAttraction(query);
              onClose();
            }}
            className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-semibold bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-brown transition-colors focus:ring-2 focus:ring-heritage-brown"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Ask Guide About This Monument</span>
          </button>
        </div>

        {/* All Monument Quick Selector */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone mb-2">
            Precinct Points of Interest
          </h4>
          <div className="space-y-1.5">
            {BELUR_ATTRACTIONS.map((attraction) => {
              const isSelected = selectedAttraction.id === attraction.id;
              return (
                <button
                  key={attraction.id}
                  onClick={() => setSelectedAttraction(attraction)}
                  className={`w-full text-left p-2 rounded-md text-xs transition-colors flex items-center justify-between ${
                    isSelected
                      ? "bg-heritage-gold/20 font-semibold text-heritage-brown dark:text-heritage-marble border border-heritage-gold/40"
                      : "hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone text-heritage-umber dark:text-heritage-stone"
                  }`}
                >
                  <span>{language === "kn" ? attraction.nameKn : attraction.nameEn}</span>
                  <span className="text-[10px] text-heritage-gold font-mono">{attraction.highlight}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
