import React, { useState, useEffect } from "react";
import {
  Activity,
  Database,
  Mic,
  Volume2,
  Languages,
  Layers,
  FileText,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Server,
  Clock,
} from "lucide-react";
import { adminApiClient } from "@/services/adminApi";
import { SystemHealth, KnowledgeGenerationItem } from "@/types/api";

export const OverviewTab: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [activeGen, setActiveGen] = useState<KnowledgeGenerationItem | null>(null);
  const [docTotal, setDocTotal] = useState<number | null>(null);
  const [syncStatus, setSyncStatus] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [healthData, genData, docListData, syncData] = await Promise.allSettled([
        adminApiClient.getHealth(),
        adminApiClient.getActiveGeneration(),
        adminApiClient.listDocuments(1, 0),
        adminApiClient.getSyncStatus(),
      ]);

      if (healthData.status === "fulfilled") {
        setHealth(healthData.value);
      }
      if (genData.status === "fulfilled") {
        setActiveGen(genData.value);
      } else {
        setActiveGen(null);
      }
      if (docListData.status === "fulfilled") {
        setDocTotal(docListData.value.total);
      }
      if (syncData.status === "fulfilled") {
        setSyncStatus(syncData.value);
      }
    } catch (err: any) {
      setErrorMessage("Failed to load some dashboard overview metrics.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  const formatUptime = (seconds?: number) => {
    if (!seconds && seconds !== 0) return "N/A";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs}h ${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div>
          <h2 className="text-xl font-bold font-display text-heritage-brown dark:text-heritage-marble">
            System & Knowledge Base Health
          </h2>
          <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
            Real-time status of Belur Chennakeshava offline inference pipelines and active generation index.
          </p>
        </div>
        <button
          onClick={fetchOverviewData}
          disabled={isLoading}
          aria-label="Refresh overview metrics"
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="p-3 rounded-lg bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300 text-xs flex items-center gap-2"
        >
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Top Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Gateway Health */}
        <div className="p-4 rounded-xl bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-heritage-umber dark:text-heritage-stone uppercase tracking-wider">
              Gateway API
            </span>
            <Server className="w-4 h-4 text-heritage-gold" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-heritage-brown dark:text-heritage-marble">
              {health?.status ? health.status.toUpperCase() : "CHECKING..."}
            </span>
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                health?.status === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
              }`}
            />
          </div>
          <p className="mt-1 text-[11px] text-heritage-umber dark:text-heritage-stone flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Uptime: {formatUptime(health?.uptime_seconds)}</span>
          </p>
        </div>

        {/* Database Status */}
        <div className="p-4 rounded-xl bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-heritage-umber dark:text-heritage-stone uppercase tracking-wider">
              Relational DB
            </span>
            <Database className="w-4 h-4 text-heritage-gold" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-heritage-brown dark:text-heritage-marble">
              {health?.components?.database?.status === "healthy" ? "CONNECTED" : "DEGRADED"}
            </span>
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                health?.components?.database?.status === "healthy" ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
          </div>
          <p className="mt-1 text-[11px] text-heritage-umber dark:text-heritage-stone">
            Dialect: {health?.components?.database?.dialect || "sqlite"} • Latency: {health?.components?.database?.latency_ms ?? 0}ms
          </p>
        </div>

        {/* Active Knowledge Generation */}
        <div className="p-4 rounded-xl bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-heritage-umber dark:text-heritage-stone uppercase tracking-wider">
              Active Generation
            </span>
            <Layers className="w-4 h-4 text-heritage-gold" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-heritage-brown dark:text-heritage-marble">
              {activeGen ? `Gen #${activeGen.generation_number}` : "NONE"}
            </span>
            {activeGen && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded">
                ACTIVE
              </span>
            )}
          </div>
          <p className="mt-1 text-[11px] text-heritage-umber dark:text-heritage-stone">
            Chunks: {activeGen?.chunk_count ?? 0} in Chroma
          </p>
        </div>

        {/* Ingested Documents */}
        <div className="p-4 rounded-xl bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-heritage-umber dark:text-heritage-stone uppercase tracking-wider">
              Heritage Documents
            </span>
            <FileText className="w-4 h-4 text-heritage-gold" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-heritage-brown dark:text-heritage-marble">
              {docTotal !== null ? docTotal : "—"}
            </span>
            <span className="text-xs text-heritage-umber dark:text-heritage-stone">PDF files</span>
          </div>
          <p className="mt-1 text-[11px] text-heritage-umber dark:text-heritage-stone">
            Deduplicated & verified
          </p>
        </div>
      </div>

      {/* Subsystem Readiness Matrix */}
      <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 p-5 shadow-xs">
        <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble mb-4 flex items-center gap-2">
          <Activity className="w-4 h-4 text-heritage-gold" />
          <span>Local AI Subsystem Readiness</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* STT */}
          <div className="p-3.5 rounded-lg bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-heritage-gold" />
                <span className="text-xs font-semibold text-heritage-brown dark:text-heritage-marble">
                  faster-whisper STT
                </span>
              </div>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                {health?.components?.speech_to_text?.status === "ready" ? "Ready" : "Available"}
              </span>
            </div>
            <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
              Device: {health?.components?.speech_to_text?.device || "CPU"} • Model: {health?.components?.speech_to_text?.model || "whisper-base"}
            </p>
          </div>

          {/* TTS */}
          <div className="p-3.5 rounded-lg bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-heritage-gold" />
                <span className="text-xs font-semibold text-heritage-brown dark:text-heritage-marble">
                  Piper Offline TTS
                </span>
              </div>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                {syncStatus?.voice?.operational ? "Operational" : "Offline"}
              </span>
            </div>
            <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
              Engine: {syncStatus?.voice?.engine || "piper"} • Installed Voices: {syncStatus?.voice?.installed_voices?.length ?? 1}
            </p>
          </div>

          {/* Translation */}
          <div className="p-3.5 rounded-lg bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Languages className="w-4 h-4 text-heritage-gold" />
                <span className="text-xs font-semibold text-heritage-brown dark:text-heritage-marble">
                  Argos Translation
                </span>
              </div>
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                KN ⇄ EN
              </span>
            </div>
            <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
              Engine: {syncStatus?.translation?.engine || "argostranslate"} • Packages: {syncStatus?.translation?.installed_packages_count ?? 2}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
