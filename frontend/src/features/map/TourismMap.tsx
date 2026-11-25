import React, { useState, useMemo } from "react";
import {
  X,
  Navigation,
  MessageSquare,
  Maximize2,
  Minimize2,
  MapPin,
  Sparkles,
  Layers,
  Search,
  BookOpen,
  Compass,
  PanelRightClose,
  PanelRightOpen,
} from "lucide-react";
import {
  UNESCO_COMPLEX_STRUCTURES,
  TEMPLE_ARCHITECTURAL_FEATURES,
  TempleAttraction,
  TempleArchitecturalFeature,
  UI_STRINGS,
} from "@/theme/tokens";
import { BelurPrecinct3D } from "./BelurPrecinct3D";

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
  const [activeLayer, setActiveLayer] = useState<"complex" | "architecture">("complex");
  const [selectedAttraction, setSelectedAttraction] = useState<TempleAttraction>(
    UNESCO_COMPLEX_STRUCTURES[0]
  );
  const [selectedArchitectureFeature, setSelectedArchitectureFeature] =
    useState<TempleArchitecturalFeature>(TEMPLE_ARCHITECTURAL_FEATURES[0]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  // Default to Fullscreen to provide an immersive 100% full-screen 3D view
  const [isFullscreen, setIsFullscreen] = useState<boolean>(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const t = UI_STRINGS[language];

  // Filtered complex structures list
  const filteredComplex = useMemo(() => {
    if (!searchQuery.trim()) return UNESCO_COMPLEX_STRUCTURES;
    const q = searchQuery.toLowerCase().trim();
    return UNESCO_COMPLEX_STRUCTURES.filter(
      (s) =>
        s.nameEn.toLowerCase().includes(q) ||
        s.nameKn.includes(q) ||
        s.categoryEn.toLowerCase().includes(q) ||
        s.categoryKn.includes(q) ||
        s.highlight.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  // Filtered architecture features list
  const filteredArchitecture = useMemo(() => {
    if (!searchQuery.trim()) return TEMPLE_ARCHITECTURAL_FEATURES;
    const q = searchQuery.toLowerCase().trim();
    return TEMPLE_ARCHITECTURAL_FEATURES.filter(
      (f) =>
        f.featureEn.toLowerCase().includes(q) ||
        f.featureKn.includes(q) ||
        f.categoryEn.toLowerCase().includes(q) ||
        f.categoryKn.includes(q) ||
        f.highlight.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  if (!isOpen) {
    return null;
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (activeLayer === "complex" && filteredComplex.length > 0) {
        setSelectedAttraction(filteredComplex[0]);
      } else if (activeLayer === "architecture" && filteredArchitecture.length > 0) {
        setSelectedArchitectureFeature(filteredArchitecture[0]);
      }
    } else if (e.key === "Escape") {
      setSearchQuery("");
    }
  };

  const handleAskGuideComplex = (attraction: TempleAttraction) => {
    const query =
      language === "kn"
        ? `${attraction.nameKn} ಬಗ್ಗೆ ವಿವರವಾಗಿ ತಿಳಿಸಿ`
        : `Tell me about the ${attraction.nameEn} at Belur.`;
    onAskAboutAttraction(query);
    onClose();
  };

  const handleAskGuideArchitecture = (feature: TempleArchitecturalFeature) => {
    const query =
      language === "kn"
        ? `ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯದ ${feature.featureKn} ವಾಸ್ತುಶಿಲ್ಪದ ಮಹತ್ವವನ್ನು ತಿಳಿಸಿ`
        : `Explain the ${feature.featureEn} architectural feature in the Belur Chennakeshava Temple.`;
    onAskAboutAttraction(query);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="map-title"
      className={`fixed z-50 bg-heritage-ivory dark:bg-heritage-carved-basalt shadow-2xl border-heritage-brown/15 dark:border-heritage-gold/20 flex flex-col transition-all duration-300 ${
        isFullscreen
          ? "inset-0 w-full h-full"
          : "inset-y-0 right-0 w-full sm:w-[580px] md:w-[680px] border-l animate-in slide-in-from-right duration-200"
      }`}
    >
      {/* Header */}
      <div className="p-3 border-b border-heritage-brown/10 dark:border-heritage-gold/15 flex items-center justify-between bg-heritage-sandstone/60 dark:bg-heritage-deep-stone/80 backdrop-blur-md z-40">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-heritage-gold/15 text-heritage-gold">
            <Navigation className="w-5 h-5" />
          </div>
          <div>
            <h2
              id="map-title"
              className="text-sm font-bold text-heritage-brown dark:text-heritage-marble flex items-center gap-1.5"
            >
              <span>{t.exploreMap}</span>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-heritage-gold text-heritage-brown">
                3D REAL
              </span>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-sky-500/15 text-sky-600 dark:text-sky-400">
                UNESCO / INTACH
              </span>
            </h2>
            <p className="text-[10px] text-heritage-umber dark:text-heritage-stone">
              {language === "kn"
                ? "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ ಸಂಕೀರ್ಣ (೧೮ ತಾಣಗಳು & ವಾಸ್ತು ಅಂಗಗಳು)"
                : "Belur Chennakeshava Temple Precinct (18 Sites & Architecture)"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Toggle Sidebar Button */}
          <button
            onClick={() => setIsSidebarOpen((prev) => !prev)}
            title={isSidebarOpen ? "Collapse Details" : "Show Details"}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-bold bg-heritage-gold/15 text-heritage-brown dark:text-heritage-gold hover:bg-heritage-gold hover:text-heritage-brown transition-all"
          >
            {isSidebarOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            <span className="hidden sm:inline">
              {isSidebarOpen ? (language === "kn" ? "ಮರೆಮಾಡಿ" : "Hide") : language === "kn" ? "ವಿವರಗಳು" : "Details"}
            </span>
          </button>

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen((prev) => !prev)}
            title={isFullscreen ? t.exitFullscreen : t.fullscreen}
            aria-label={isFullscreen ? "Exit Fullscreen" : "Fullscreen 3D Map"}
            className="p-1.5 rounded-md text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone transition-colors"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Close Modal */}
          <button
            onClick={onClose}
            aria-label="Close precinct map"
            className="p-1.5 rounded-md text-heritage-umber dark:text-heritage-stone hover:text-heritage-terracotta hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main 3D Canvas Viewport: Spans 100% of modal */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        <BelurPrecinct3D
          selectedAttraction={selectedAttraction}
          onSelectAttraction={setSelectedAttraction}
          selectedArchitectureFeature={selectedArchitectureFeature}
          onSelectArchitectureFeature={setSelectedArchitectureFeature}
          activeLayer={activeLayer}
          onLayerChange={setActiveLayer}
          language={language}
          isFullscreen={isFullscreen}
          onToggleFullscreen={() => setIsFullscreen((prev) => !prev)}
          isDark={typeof document !== "undefined" && document.documentElement.classList.contains("dark")}
        />

        {/* Floating Sidebar: Glass Details & Discovery Directory */}
        {isSidebarOpen && (
          <div
            className={`absolute z-30 transition-all duration-300 flex flex-col bg-heritage-ivory/95 dark:bg-heritage-carved-basalt/95 backdrop-blur-md border border-heritage-brown/15 dark:border-heritage-gold/25 shadow-2xl rounded-2xl overflow-hidden ${
              isFullscreen
                ? "top-16 bottom-16 right-4 w-full sm:w-[400px] md:w-[440px] max-h-[calc(100vh-140px)]"
                : "inset-y-0 right-0 w-full sm:w-[380px] border-l"
            }`}
          >
            {/* Sidebar Header with Layer Tabs */}
            <div className="p-3 border-b border-heritage-brown/10 dark:border-heritage-gold/15 bg-heritage-sandstone/40 dark:bg-heritage-deep-stone/60 flex items-center justify-between gap-1.5">
              <div className="flex items-center gap-1 p-0.5 rounded-lg bg-heritage-sandstone dark:bg-heritage-deep-stone flex-1">
                <button
                  onClick={() => {
                    setActiveLayer("complex");
                    setSearchQuery("");
                  }}
                  className={`flex-1 px-2.5 py-1.5 rounded-md text-xs font-bold transition-all flex items-center justify-center gap-1 ${
                    activeLayer === "complex"
                      ? "bg-heritage-gold text-heritage-brown shadow-xs"
                      : "text-heritage-umber dark:text-heritage-stone hover:text-heritage-gold"
                  }`}
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span className="truncate">{t.complexTab}</span>
                </button>

                <button
                  onClick={() => {
                    setActiveLayer("architecture");
                    setSearchQuery("");
                  }}
                  className={`flex-1 px-2.5 py-1.5 rounded-md text-xs font-bold transition-all flex items-center justify-center gap-1 ${
                    activeLayer === "architecture"
                      ? "bg-sky-500 text-white shadow-xs"
                      : "text-heritage-umber dark:text-heritage-stone hover:text-sky-400"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span className="truncate">{t.architectureTab}</span>
                </button>
              </div>

              <button
                onClick={() => setIsSidebarOpen(false)}
                title="Collapse Panel"
                className="p-1 rounded-md text-heritage-umber hover:text-heritage-gold"
              >
                <PanelRightClose className="w-4 h-4" />
              </button>
            </div>

            {/* Pinned Quick Search Bar at Top of Sidebar */}
            <div className="p-2.5 border-b border-heritage-brown/10 dark:border-heritage-gold/15 bg-heritage-sandstone/30 dark:bg-heritage-deep-stone/50">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-heritage-umber dark:text-heritage-stone absolute left-2.5 top-2.5 pointer-events-none" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleSearchKeyDown}
                  onClick={(e) => e.stopPropagation()}
                  placeholder={t.searchPlacesPlaceholder}
                  aria-label={t.searchPlacesPlaceholder}
                  className="w-full pl-8 pr-7 py-1.5 text-xs rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/25 bg-heritage-ivory dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble placeholder:text-heritage-umber/60 dark:placeholder:text-heritage-stone/60 focus:outline-none focus:ring-1 focus:ring-heritage-gold cursor-text shadow-xs"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2 top-1.5 text-heritage-umber hover:text-heritage-gold p-0.5 rounded transition-colors"
                    title="Clear search"
                    aria-label="Clear search"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Sidebar Content (Scrollable) */}
            <div className="flex-1 overflow-y-auto p-3.5 space-y-3">
              {/* Spotlight Card */}
              {activeLayer === "complex" ? (
                <div className="p-3.5 rounded-xl bg-gradient-to-br from-heritage-sandstone/90 to-heritage-sandstone/40 dark:from-heritage-deep-stone/90 dark:to-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/25 shadow-sm">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-heritage-gold uppercase tracking-wider">
                      <Sparkles className="w-3 h-3" />
                      {selectedAttraction.highlight}
                    </span>
                    <span className="text-[10px] font-mono text-heritage-umber dark:text-heritage-stone">
                      {selectedAttraction.lat.toFixed(4)}° N, {selectedAttraction.lng.toFixed(4)}° E
                    </span>
                  </div>

                  <div className="mb-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                    {language === "kn" ? selectedAttraction.categoryKn : selectedAttraction.categoryEn}
                  </div>

                  <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble mb-2 flex items-center gap-1.5">
                    <MapPin className="w-4 h-4 text-heritage-gold flex-shrink-0" />
                    <span>{language === "kn" ? selectedAttraction.nameKn : selectedAttraction.nameEn}</span>
                  </h3>

                  <p className="text-xs text-heritage-umber dark:text-heritage-stone leading-relaxed mb-2.5">
                    {language === "kn" ? selectedAttraction.descriptionKn : selectedAttraction.descriptionEn}
                  </p>

                  {selectedAttraction.architecturalDetailsEn && (
                    <div className="p-2 rounded-lg bg-heritage-ivory/80 dark:bg-heritage-deep-stone/80 border border-heritage-brown/10 dark:border-heritage-gold/20 text-[11px] text-heritage-umber dark:text-heritage-stone leading-relaxed">
                      <span className="font-bold text-heritage-gold flex items-center gap-1 mb-0.5">
                        <BookOpen className="w-3 h-3" />
                        {language === "kn" ? "ವಾಸ್ತು ವಿವರಣೆ:" : "Architectural Profile:"}
                      </span>
                      {language === "kn"
                        ? selectedAttraction.architecturalDetailsKn
                        : selectedAttraction.architecturalDetailsEn}
                    </div>
                  )}

                  {/* Ask Guide CTA */}
                  <button
                    onClick={() => handleAskGuideComplex(selectedAttraction)}
                    className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-bold bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-brown transition-all shadow-sm active:scale-[0.98]"
                  >
                    <MessageSquare className="w-4 h-4" />
                    <span>{t.askAboutMonument}</span>
                  </button>
                </div>
              ) : (
                <div className="p-3.5 rounded-xl bg-gradient-to-br from-sky-50 dark:from-sky-950/40 to-heritage-sandstone/40 dark:to-heritage-deep-stone/40 border border-sky-400/30 dark:border-sky-500/30 shadow-sm">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-sky-600 dark:text-sky-400 uppercase tracking-wider">
                      <Sparkles className="w-3 h-3" />
                      {selectedArchitectureFeature.highlight}
                    </span>
                    <span className="text-[10px] font-mono text-heritage-umber dark:text-heritage-stone">
                      {language === "kn"
                        ? selectedArchitectureFeature.categoryKn
                        : selectedArchitectureFeature.categoryEn}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble mb-2 flex items-center gap-1.5">
                    <Compass className="w-4 h-4 text-sky-500 flex-shrink-0" />
                    <span>
                      {selectedArchitectureFeature.featureEn} ({selectedArchitectureFeature.featureKn})
                    </span>
                  </h3>

                  <p className="text-xs text-heritage-umber dark:text-heritage-stone leading-relaxed">
                    {language === "kn"
                      ? selectedArchitectureFeature.descriptionKn
                      : selectedArchitectureFeature.descriptionEn}
                  </p>

                  {/* Ask Guide Architecture CTA */}
                  <button
                    onClick={() => handleAskGuideArchitecture(selectedArchitectureFeature)}
                    className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-bold bg-sky-500 hover:bg-sky-600 text-white transition-all shadow-sm active:scale-[0.98]"
                  >
                    <MessageSquare className="w-4 h-4" />
                    <span>
                      {language === "kn"
                        ? "ಈ ವಾಸ್ತು ಅಂಗದ ಬಗ್ಗೆ ಕೇಳಿ"
                        : `Ask Guide About ${selectedArchitectureFeature.featureEn}`}
                    </span>
                  </button>
                </div>
              )}

              {/* Directory Section Header & List */}
              <div className="space-y-2">
                <div className="flex items-center justify-between pt-1">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone">
                    {activeLayer === "complex"
                      ? language === "kn"
                        ? "ಯುನೆಸ್ಕೋ ಸಂಕೀರ್ಣದ ೧೮ ತಾಣಗಳು"
                        : "18 UNESCO Complex Sites"
                      : language === "kn"
                      ? "ಮುಖ್ಯ ದೇವಾಲಯದ ೬ ವಾಸ್ತುಶಿಲ್ಪ ಅಂಗಗಳು"
                      : "6 Architectural Anatomy Zones"}
                  </h4>
                  <span className="text-[10px] font-mono text-heritage-gold font-bold">
                    {activeLayer === "complex"
                      ? `${filteredComplex.length} / 18`
                      : `${filteredArchitecture.length} / 6`}
                  </span>
                </div>

                {/* Empty Search Results Feedback */}
                {activeLayer === "complex" && filteredComplex.length === 0 && (
                  <div className="p-4 text-center text-xs text-heritage-umber dark:text-heritage-stone rounded-lg bg-heritage-sandstone/30 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15 space-y-1.5">
                    <p>{language === "kn" ? "ಯಾವುದೇ ತಾಣಗಳು ಕಂಡುಬಂದಿಲ್ಲ" : "No matching sites found"}</p>
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="text-xs text-heritage-gold hover:underline font-semibold"
                    >
                      {language === "kn" ? "ಹುಡುಕಾಟ ತೆರವುಗೊಳಿಸಿ" : "Clear search query"}
                    </button>
                  </div>
                )}

                {activeLayer === "architecture" && filteredArchitecture.length === 0 && (
                  <div className="p-4 text-center text-xs text-heritage-umber dark:text-heritage-stone rounded-lg bg-heritage-sandstone/30 dark:bg-heritage-deep-stone/40 border border-heritage-brown/10 dark:border-heritage-gold/15 space-y-1.5">
                    <p>{language === "kn" ? "ಯಾವುದೇ ವಾಸ್ತುಶಿಲ್ಪ ಅಂಗಗಳು ಕಂಡುಬಂದಿಲ್ಲ" : "No matching architectural zones found"}</p>
                    <button
                      type="button"
                      onClick={() => setSearchQuery("")}
                      className="text-xs text-heritage-gold hover:underline font-semibold"
                    >
                      {language === "kn" ? "ಹುಡುಕಾಟ ತೆರವುಗೊಳಿಸಿ" : "Clear search query"}
                    </button>
                  </div>
                )}

                {/* List Directory */}
                <div className="space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                  {activeLayer === "complex"
                    ? filteredComplex.map((attraction) => {
                        const isSelected = selectedAttraction.id === attraction.id;
                        return (
                          <button
                            key={attraction.id}
                            onClick={() => setSelectedAttraction(attraction)}
                            className={`w-full text-left p-2 rounded-lg text-xs transition-all flex items-center justify-between ${
                              isSelected
                                ? "bg-heritage-gold/20 font-bold text-heritage-brown dark:text-heritage-marble border border-heritage-gold/50 shadow-xs"
                                : "hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone text-heritage-umber dark:text-heritage-stone border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span
                                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold flex-shrink-0 ${
                                  isSelected
                                    ? "bg-heritage-gold text-heritage-brown"
                                    : "bg-heritage-sandstone dark:bg-heritage-deep-stone text-heritage-umber dark:text-heritage-stone"
                                }`}
                              >
                                {attraction.unescoNumber}
                              </span>
                              <span className="truncate">
                                {language === "kn" ? attraction.nameKn : attraction.nameEn}
                              </span>
                            </div>
                            <span className="text-[10px] text-heritage-gold font-mono ml-2 flex-shrink-0">
                              {attraction.highlight}
                            </span>
                          </button>
                        );
                      })
                    : filteredArchitecture.map((feature, idx) => {
                        const isSelected = selectedArchitectureFeature.id === feature.id;
                        return (
                          <button
                            key={feature.id}
                            onClick={() => setSelectedArchitectureFeature(feature)}
                            className={`w-full text-left p-2 rounded-lg text-xs transition-all flex items-center justify-between ${
                              isSelected
                                ? "bg-sky-500/20 font-bold text-heritage-brown dark:text-heritage-marble border border-sky-400/50 shadow-xs"
                                : "hover:bg-heritage-sandstone dark:hover:bg-heritage-deep-stone text-heritage-umber dark:text-heritage-stone border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span
                                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold flex-shrink-0 ${
                                  isSelected
                                    ? "bg-sky-500 text-white"
                                    : "bg-heritage-sandstone dark:bg-heritage-deep-stone text-heritage-umber dark:text-heritage-stone"
                                }`}
                              >
                                {idx + 1}
                              </span>
                              <span className="truncate">
                                {feature.featureEn} ({feature.featureKn})
                              </span>
                            </div>
                            <span className="text-[10px] text-sky-500 font-mono ml-2 flex-shrink-0">
                              {feature.highlight}
                            </span>
                          </button>
                        );
                      })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
