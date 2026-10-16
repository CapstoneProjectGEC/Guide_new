import React, { useState } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { CitationDrawer } from "@/features/citations/CitationDrawer";
import { TourismMap } from "@/features/map/TourismMap";
import { Citation } from "@/types/api";

interface LayoutProps {
  language: "kn" | "en";
  onLanguageChange: (lang: "kn" | "en") => void;
  audioEnabled: boolean;
  onAudioToggle: () => void;
  isDark: boolean;
  onThemeToggle: () => void;
  onNewSession: () => void;
  onSelectAttraction: (query: string) => void;
  activeCitation: Citation | null;
  onCloseCitation: () => void;
  onOpenAdmin?: () => void;
  onOpenAboutKb?: () => void;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  language,
  onLanguageChange,
  audioEnabled,
  onAudioToggle,
  isDark,
  onThemeToggle,
  onNewSession,
  onSelectAttraction,
  activeCitation,
  onCloseCitation,
  onOpenAdmin,
  onOpenAboutKb,
  children,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-heritage-ivory dark:bg-heritage-basalt text-heritage-brown dark:text-heritage-marble font-sans">
      {/* Top Navigation */}
      <Header
        language={language}
        onLanguageChange={onLanguageChange}
        audioEnabled={audioEnabled}
        onAudioToggle={onAudioToggle}
        isDark={isDark}
        onThemeToggle={onThemeToggle}
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        onToggleMap={() => setMapOpen((prev) => !prev)}
        onOpenAdmin={onOpenAdmin}
        onOpenAboutKb={onOpenAboutKb}
      />

      {/* Main Body (Sidebar + Center Chat + Side Drawers) */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Desktop Left Sidebar */}
        <div className="hidden md:block">
          <Sidebar
            language={language}
            onNewSession={onNewSession}
            onSelectAttraction={onSelectAttraction}
          />
        </div>

        {/* Mobile Slide-over Sidebar */}
        {sidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden flex">
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-xs"
              onClick={() => setSidebarOpen(false)}
            />
            <div className="relative z-50">
              <Sidebar
                language={language}
                onNewSession={onNewSession}
                onSelectAttraction={onSelectAttraction}
                onCloseMobile={() => setSidebarOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Center Viewport */}
        <main className="flex-1 flex flex-col h-full overflow-hidden bg-heritage-ivory dark:bg-heritage-basalt">
          {children}
        </main>

        {/* Citation Inspection Drawer */}
        <CitationDrawer
          citation={activeCitation}
          isOpen={activeCitation !== null}
          onClose={onCloseCitation}
          language={language}
        />

        {/* Precinct Map Drawer */}
        <TourismMap
          isOpen={mapOpen}
          onClose={() => setMapOpen(false)}
          language={language}
          onAskAboutAttraction={(query) => {
            onSelectAttraction(query);
            setMapOpen(false);
          }}
        />
      </div>
    </div>
  );
};
