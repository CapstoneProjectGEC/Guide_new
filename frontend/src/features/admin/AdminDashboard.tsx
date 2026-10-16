import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  FileText,
  Layers,
  Volume2,
  Activity,
  LogOut,
  ArrowLeft,
  User,
} from "lucide-react";
import { authService } from "@/services/auth";
import { AdminRoleType } from "@/types/api";
import { OverviewTab } from "./OverviewTab";
import { DocumentManager } from "./DocumentManager";
import { GenerationManager } from "./GenerationManager";
import { ModelSyncTab } from "./ModelSyncTab";
import { DiagnosticsTab } from "./DiagnosticsTab";

interface AdminDashboardProps {
  onExit: () => void;
}

type TabKey = "overview" | "documents" | "generations" | "models" | "diagnostics";

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onExit }) => {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [role, setRole] = useState<AdminRoleType | null>(authService.getRole());
  const [username, setUsername] = useState<string | null>(authService.getUsername());

  useEffect(() => {
    const unsubscribe = authService.subscribe((isAuth, currentRole) => {
      if (!isAuth) {
        onExit();
      } else {
        setRole(currentRole);
        setUsername(authService.getUsername());
      }
    });
    return unsubscribe;
  }, [onExit]);

  const handleLogout = async () => {
    await authService.logout();
    onExit();
  };

  const getRoleBadge = (r: AdminRoleType | null) => {
    switch (r) {
      case "SUPER_ADMIN":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "SITE_CURATOR":
        return "bg-heritage-gold/20 text-heritage-brown dark:text-heritage-gold border-heritage-gold/30";
      case "OPERATOR":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
      default:
        return "bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20";
    }
  };

  const tabs = [
    { key: "overview" as TabKey, label: "Overview", icon: LayoutDashboard },
    { key: "documents" as TabKey, label: "Documents", icon: FileText },
    { key: "generations" as TabKey, label: "Pipeline & Generations", icon: Layers },
    { key: "models" as TabKey, label: "Models & Translation", icon: Volume2 },
    { key: "diagnostics" as TabKey, label: "Retrieval Diagnostics", icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-heritage-ivory dark:bg-heritage-basalt text-heritage-brown dark:text-heritage-marble transition-colors flex flex-col font-sans">
      {/* Top Administrative Header */}
      <header className="sticky top-0 z-30 bg-white/95 dark:bg-heritage-carved-basalt/95 backdrop-blur-md border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Left: Branding & Back Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={onExit}
              title="Return to Public Tourist Guide"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-heritage-brown dark:text-heritage-marble hover:bg-heritage-sandstone dark:hover:bg-heritage-stone-dark transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Tourist View</span>
            </button>

            <div className="h-4 w-px bg-heritage-brown/15 dark:bg-heritage-gold/20 hidden sm:block" />

            <div className="flex items-center gap-2">
              <span className="text-xl" role="img" aria-label="Shield Crest">
                🛡️
              </span>
              <div>
                <h1 className="text-sm sm:text-base font-bold font-display text-heritage-brown dark:text-heritage-marble leading-tight">
                  Heritage Administration
                </h1>
                <p className="text-[10px] text-heritage-umber dark:text-heritage-stone hidden sm:block">
                  Belur Chennakeshava Knowledge Governance
                </p>
              </div>
            </div>
          </div>

          {/* Right: Identity, Role & Logout */}
          <div className="flex items-center gap-3">
            {/* Authenticated Admin Identity */}
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10 text-xs">
              <User className="w-3.5 h-3.5 text-heritage-gold" />
              <span className="font-semibold">{username || "Administrator"}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold border uppercase ${getRoleBadge(
                  role
                )}`}
              >
                {role || "VIEWER"}
              </span>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              title="Sign out administrator"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold text-heritage-terracotta hover:bg-heritage-terracotta/10 border border-heritage-terracotta/20 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation Bar */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav
            role="tablist"
            aria-label="Admin Navigation Tabs"
            className="flex items-center space-x-1 sm:space-x-4 overflow-x-auto py-2 no-scrollbar"
          >
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isSelected = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  role="tab"
                  id={`tab-${tab.key}`}
                  aria-selected={isSelected}
                  aria-controls={`tabpanel-${tab.key}`}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                    isSelected
                      ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                      : "text-heritage-umber dark:text-heritage-stone hover:text-heritage-brown dark:hover:text-heritage-marble hover:bg-heritage-sandstone/50 dark:hover:bg-heritage-stone-dark/50"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Tab Panels */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {activeTab === "overview" && <OverviewTab />}
          {activeTab === "documents" && <DocumentManager />}
          {activeTab === "generations" && <GenerationManager />}
          {activeTab === "models" && <ModelSyncTab />}
          {activeTab === "diagnostics" && <DiagnosticsTab />}
        </div>
      </main>
    </div>
  );
};
