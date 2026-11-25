import React, { useState, useEffect } from "react";
import {
  Volume2,
  Languages,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Lock,
  ShieldCheck,
} from "lucide-react";
import { adminApiClient } from "@/services/adminApi";
import { authService } from "@/services/auth";
import { ModelSyncStatusResponse, VoiceSyncResponse, TranslationSyncResponse } from "@/types/api";

export const ModelSyncTab: React.FC = () => {
  const [syncStatus, setSyncStatus] = useState<ModelSyncStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncingVoice, setIsSyncingVoice] = useState<boolean>(false);
  const [isSyncingTrans, setIsSyncingTrans] = useState<boolean>(false);
  const [voiceSyncResult, setVoiceSyncResult] = useState<VoiceSyncResponse | null>(null);
  const [transSyncResult, setTransSyncResult] = useState<TranslationSyncResponse | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const canOperate = authService.hasRole("OPERATOR");

  const loadSyncStatus = async () => {
    setIsLoading(true);
    try {
      const data = await adminApiClient.getSyncStatus();
      setSyncStatus(data);
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to load model registry synchronization status.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSyncStatus();
  }, []);

  const handleSyncVoices = async () => {
    setIsSyncingVoice(true);
    setNotification(null);
    try {
      const res = await adminApiClient.syncVoices();
      setVoiceSyncResult(res);
      setNotification({
        type: "success",
        message: `Successfully synchronized ${res.synced_voices_count} Piper voice models into voice_registry.`,
      });
      await loadSyncStatus();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Voice registry synchronization failed.",
      });
    } finally {
      setIsSyncingVoice(false);
    }
  };

  const handleSyncTranslation = async () => {
    setIsSyncingTrans(true);
    setNotification(null);
    try {
      const res = await adminApiClient.syncTranslation();
      setTransSyncResult(res);
      setNotification({
        type: "success",
        message: `Successfully synchronized ${res.synced_packages_count} Argos neural translation packages into translation_registry.`,
      });
      await loadSyncStatus();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Translation registry synchronization failed.",
      });
    } finally {
      setIsSyncingTrans(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div>
          <h2 className="text-xl font-bold font-display text-heritage-brown dark:text-heritage-marble">
            Voice & Translation Model Registry
          </h2>
          <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
            Offline speech synthesis voices and neural translation packages provisioned on local host.
          </p>
        </div>

        <button
          onClick={loadSyncStatus}
          disabled={isLoading}
          aria-label="Refresh model registry status"
          className="inline-flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Offline Constraint Notice */}
      <div className="p-3.5 rounded-lg bg-heritage-gold/10 dark:bg-heritage-gold/15 border border-heritage-gold/20 text-heritage-brown dark:text-heritage-gold text-xs flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-heritage-gold" />
        <span>
          <strong>Air-Gapped Offline Operation:</strong> All speech models (Piper ONNX) and translation packages (Argos) run locally without cloud API calls or online model downloads. Registry synchronization reconciles discovered local models into MySQL tables.
        </span>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          role="alert"
          className={`p-3 rounded-lg text-xs flex items-center justify-between animate-in fade-in duration-200 ${
            notification.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-xs underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Grid of Subsystems */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Piper TTS Subsystem */}
        <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-gold">
                  <Volume2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
                    Piper Text-to-Speech
                  </h3>
                  <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
                    Engine: {syncStatus?.voice?.engine || "piper"}
                  </p>
                </div>
              </div>

              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                  syncStatus?.voice?.operational
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                }`}
              >
                {syncStatus?.voice?.operational ? "Operational" : "Unavailable"}
              </span>
            </div>

            <div className="space-y-2 mb-6">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone">
                Installed Offline Voices
              </h4>
              {syncStatus?.voice?.installed_voices && syncStatus.voice.installed_voices.length > 0 ? (
                <ul className="divide-y divide-heritage-brown/5 dark:divide-heritage-gold/10 text-xs font-mono">
                  {syncStatus.voice.installed_voices.map((v, i) => (
                    <li key={i} className="py-1.5 flex items-center justify-between">
                      <span>{v}</span>
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400">Ready</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-heritage-umber dark:text-heritage-stone italic">
                  No local voices currently detected in piper storage directory.
                </p>
              )}
              {voiceSyncResult && (
                <div className="mt-2 p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-700 dark:text-emerald-300">
                  Last Sync: {voiceSyncResult.synced_voices_count} voices reconciled by {voiceSyncResult.synced_by}
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-heritage-brown/10 dark:border-heritage-gold/10 flex items-center justify-between">
            <span className="text-xs text-heritage-umber dark:text-heritage-stone">
              Target: MySQL voice_registry
            </span>
            {canOperate ? (
              <button
                onClick={handleSyncVoices}
                disabled={isSyncingVoice}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-midnight-basalt shadow-xs transition-colors disabled:opacity-50"
              >
                {isSyncingVoice ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Syncing...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Sync Voices</span>
                  </>
                )}
              </button>
            ) : (
              <div
                title="Sync requires OPERATOR or higher role"
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-stone-dark text-heritage-umber dark:text-heritage-stone opacity-60 cursor-not-allowed"
              >
                <Lock className="w-3 h-3" />
                <span>Operator Required</span>
              </div>
            )}
          </div>
        </div>

        {/* Argos Translation Subsystem */}
        <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-gold">
                  <Languages className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
                    Argos Neural Translation
                  </h3>
                  <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
                    Engine: {syncStatus?.translation?.engine || "argostranslate"}
                  </p>
                </div>
              </div>

              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                  (syncStatus?.translation?.installed_packages_count ?? 0) > 0
                    ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                    : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                }`}
              >
                {(syncStatus?.translation?.installed_packages_count ?? 0) > 0 ? "Active" : "Offline Fallback Active"}
              </span>
            </div>

            <div className="space-y-3 mb-6">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone">
                Language Model Pairs
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-lg bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10">
                  <span className="font-semibold block">Kannada → English</span>
                  <span className={`text-[10px] ${syncStatus?.translation?.kn_en_available ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                    {syncStatus?.translation?.kn_en_available ? "Installed & Operational" : "Glossary & Transliteration Fallback"}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-heritage-sandstone/60 dark:bg-heritage-stone-dark/60 border border-heritage-brown/5 dark:border-heritage-gold/10">
                  <span className="font-semibold block">English → Kannada</span>
                  <span className={`text-[10px] ${syncStatus?.translation?.en_kn_available ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>
                    {syncStatus?.translation?.en_kn_available ? "Installed & Operational" : "Bilingual Prompt Fallback"}
                  </span>
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-heritage-gold/5 dark:bg-heritage-gold/10 border border-heritage-gold/15 text-[11px] text-heritage-umber dark:text-heritage-stone leading-relaxed">
                <strong>Kannada Offline Architecture:</strong> Upstream Argos Translate does not publish official Kannada language packages. Kannada queries are safely handled completely offline via the built-in Heritage Entity Glossary, Term Normalizer, and bilingual LLM synthesis.
              </div>
              <p className="text-[11px] text-heritage-umber dark:text-heritage-stone">
                Total Installed Packages: {syncStatus?.translation?.installed_packages_count ?? 0}
              </p>
              {transSyncResult && (
                <div className="mt-2 p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-700 dark:text-emerald-300">
                  Last Sync: {transSyncResult.synced_packages_count} neural models reconciled by {transSyncResult.synced_by}
                </div>
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-heritage-brown/10 dark:border-heritage-gold/10 flex items-center justify-between">
            <span className="text-xs text-heritage-umber dark:text-heritage-stone">
              Target: MySQL translation_registry
            </span>
            {canOperate ? (
              <button
                onClick={handleSyncTranslation}
                disabled={isSyncingTrans}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-midnight-basalt shadow-xs transition-colors disabled:opacity-50"
              >
                {isSyncingTrans ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Syncing...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Sync Packages</span>
                  </>
                )}
              </button>
            ) : (
              <div
                title="Sync requires OPERATOR or higher role"
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-stone-dark text-heritage-umber dark:text-heritage-stone opacity-60 cursor-not-allowed"
              >
                <Lock className="w-3 h-3" />
                <span>Operator Required</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
