import React from "react";
import { Languages, Volume2, VolumeX, Moon, Sun, Menu, Compass, Shield } from "lucide-react";
import { UI_STRINGS } from "@/theme/tokens";

interface HeaderProps {
  language: "kn" | "en";
  onLanguageChange: (lang: "kn" | "en") => void;
  audioEnabled: boolean;
  onAudioToggle: () => void;
  isDark: boolean;
  onThemeToggle: () => void;
  onToggleSidebar: () => void;
  onToggleMap: () => void;
  onOpenAdmin?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  language,
  onLanguageChange,
  audioEnabled,
  onAudioToggle,
  isDark,
  onThemeToggle,
  onToggleSidebar,
  onToggleMap,
  onOpenAdmin,
}) => {
  const t = UI_STRINGS[language];

  return (
    <header className="sticky top-0 z-30 bg-heritage-ivory/95 dark:bg-heritage-basalt/95 backdrop-blur-md border-b border-heritage-brown/10 dark:border-heritage-gold/15 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Mobile Nav Button & Brand */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            aria-label="Toggle navigation menu"
            className="md:hidden p-2 rounded-md text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt transition-colors focus:ring-2 focus:ring-heritage-gold"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2.5">
            <span className="text-2xl select-none" role="img" aria-label="Temple Crest">
              🛕
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-bold font-display tracking-tight text-heritage-brown dark:text-heritage-marble">
                  {t.monumentName}
                </h1>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-heritage-forest/10 text-heritage-forest dark:bg-emerald-500/20 dark:text-emerald-300">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 animate-pulse" />
                  {t.offlineMode}
                </span>
              </div>
              <p className="text-xs text-heritage-umber dark:text-heritage-stone hidden sm:block">
                {t.subtitle}
              </p>
            </div>
          </div>
        </div>

        {/* Right: Controls (Language, Audio, Theme, Map) */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          {/* Map & Attractions Toggle */}
          <button
            onClick={onToggleMap}
            aria-label={t.exploreMap}
            title={t.exploreMap}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors focus:ring-2 focus:ring-heritage-gold"
          >
            <Compass className="w-4 h-4 text-heritage-gold" />
            <span className="hidden lg:inline">{t.exploreMap}</span>
          </button>

          {/* Language Switcher */}
          <button
            onClick={() => onLanguageChange(language === "kn" ? "en" : "kn")}
            aria-label="Switch language between Kannada and English"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-semibold bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors focus:ring-2 focus:ring-heritage-gold"
          >
            <Languages className="w-4 h-4 text-heritage-gold" />
            <span>{language === "kn" ? "English" : "ಕನ್ನಡ"}</span>
          </button>

          {/* Audio Mute/Unmute */}
          <button
            onClick={onAudioToggle}
            aria-label={audioEnabled ? t.muteAudio : t.unmuteAudio}
            title={audioEnabled ? t.muteAudio : t.unmuteAudio}
            className="p-2 rounded-md text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt transition-colors focus:ring-2 focus:ring-heritage-gold"
          >
            {audioEnabled ? (
              <Volume2 className="w-4 h-4 text-heritage-gold" />
            ) : (
              <VolumeX className="w-4 h-4 text-heritage-umber dark:text-heritage-stone" />
            )}
          </button>

          {/* Light/Dark Toggle */}
          <button
            onClick={onThemeToggle}
            aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
            className="p-2 rounded-md text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt transition-colors focus:ring-2 focus:ring-heritage-gold"
          >
            {isDark ? (
              <Sun className="w-4 h-4 text-heritage-gold" />
            ) : (
              <Moon className="w-4 h-4 text-heritage-brown" />
            )}
          </button>

          {/* Admin Portal Toggle */}
          {onOpenAdmin && (
            <button
              onClick={onOpenAdmin}
              aria-label="Access Heritage Administrator Portal"
              title="Admin Portal"
              className="p-2 rounded-md text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-carved-basalt hover:text-heritage-gold transition-colors focus:ring-2 focus:ring-heritage-gold"
            >
              <Shield className="w-4 h-4 text-heritage-gold" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
