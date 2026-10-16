import React, { useState, useEffect, useRef } from "react";
import {
  Layers,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  Award,
  Lock,
} from "lucide-react";
import { adminApiClient } from "@/services/adminApi";
import { authService } from "@/services/auth";
import { KnowledgeGenerationItem } from "@/types/api";

export const GenerationManager: React.FC = () => {
  const [generations, setGenerations] = useState<KnowledgeGenerationItem[]>([]);
  const [activeGenId, setActiveGenId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isBuilding, setIsBuilding] = useState<boolean>(false);
  const [isPromoting, setIsPromoting] = useState<string | null>(null);
  const [rollbackModalOpen, setRollbackModalOpen] = useState<boolean>(false);
  const [rollbackTargetId, setRollbackTargetId] = useState<string>("");
  const [isRollingBack, setIsRollingBack] = useState<boolean>(false);
  const [expandedGenId, setExpandedGenId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pollCountRef = useRef<number>(0);
  const canCurate = authService.hasRole("SITE_CURATOR");

  const loadGenerations = async (silent: boolean = false) => {
    if (!silent) setIsLoading(true);
    try {
      const res = await adminApiClient.listGenerations();
      setGenerations(res.generations);
      setActiveGenId(res.active_generation_id);

      // Check if any generation is currently building/in-progress
      const hasActiveBuild = res.generations.some((g) =>
        ["BUILD", "PARSE", "CHUNK", "EMBED", "INDEX", "VALIDATE"].includes(g.status)
      );

      if (hasActiveBuild && pollCountRef.current < 30) {
        // Bounded polling every 3 seconds (max 30 iterations = 90s)
        clearTimeout(pollingTimerRef.current as any);
        pollingTimerRef.current = setTimeout(() => {
          pollCountRef.current += 1;
          loadGenerations(true);
        }, 3000);
      } else {
        pollCountRef.current = 0;
      }
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to load knowledge generations.",
      });
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGenerations();
    return () => {
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
      }
    };
  }, []);

  const handleBuildGeneration = async () => {
    setIsBuilding(true);
    setNotification(null);
    try {
      const newGen = await adminApiClient.buildGeneration();
      setNotification({
        type: "success",
        message: `Generation #${newGen.generation_number} build initiated successfully.`,
      });
      pollCountRef.current = 0;
      await loadGenerations();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to start generation build.",
      });
    } finally {
      setIsBuilding(false);
    }
  };

  const handlePromote = async (genId: string) => {
    setIsPromoting(genId);
    setNotification(null);
    try {
      const promoted = await adminApiClient.promoteGeneration(genId);
      setNotification({
        type: "success",
        message: `Generation #${promoted.generation_number} is now ACTIVE.`,
      });
      await loadGenerations();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Failed to promote generation.",
      });
    } finally {
      setIsPromoting(null);
    }
  };

  const handleRollback = async () => {
    if (!rollbackTargetId) return;
    setIsRollingBack(true);
    try {
      const rolledBack = await adminApiClient.rollbackGeneration(rollbackTargetId);
      setNotification({
        type: "success",
        message: `Instantly rolled back to Generation #${rolledBack.generation_number} (Status: ACTIVE).`,
      });
      setRollbackModalOpen(false);
      setRollbackTargetId("");
      await loadGenerations();
    } catch (err: any) {
      setNotification({
        type: "error",
        message: err.message || "Rollback failed.",
      });
    } finally {
      setIsRollingBack(false);
    }
  };

  const getStatusBadge = (status: string, isActive: boolean) => {
    if (isActive) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-heritage-gold/20 text-heritage-brown dark:text-heritage-gold border border-heritage-gold/30">
          <Award className="w-3 h-3 text-heritage-gold" />
          ACTIVE
        </span>
      );
    }

    switch (status) {
      case "ARCHIVED":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-umber dark:text-heritage-stone">
            ARCHIVED
          </span>
        );
      case "FAILED":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-heritage-terracotta/10 text-heritage-terracotta dark:text-red-400">
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <div>
          <h2 className="text-xl font-bold font-display text-heritage-brown dark:text-heritage-marble">
            Knowledge Base Pipeline & Generations
          </h2>
          <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
            Immutable versioned RAG collections with atomic instant rollback (&lt;100ms).
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canCurate ? (
            <>
              {/* Build Generation Button */}
              <button
                onClick={handleBuildGeneration}
                disabled={isBuilding}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-midnight-basalt shadow-xs disabled:opacity-50 transition-colors"
              >
                {isBuilding ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Trigger Build</span>
                  </>
                )}
              </button>

              {/* Instant Rollback Button */}
              <button
                onClick={() => setRollbackModalOpen(true)}
                disabled={generations.length < 2}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent disabled:opacity-40 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Instant Rollback</span>
              </button>
            </>
          ) : (
            <div
              title="Pipeline management requires SITE_CURATOR role"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-carved-basalt text-heritage-umber dark:text-heritage-stone opacity-60 cursor-not-allowed"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Curator Required</span>
            </div>
          )}

          <button
            onClick={() => loadGenerations()}
            disabled={isLoading}
            aria-label="Refresh generations"
            className="p-2 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
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

      {/* Generations List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="py-12 text-center text-heritage-umber dark:text-heritage-stone bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-heritage-gold" />
            <span>Retrieving knowledge generations...</span>
          </div>
        ) : generations.length === 0 ? (
          <div className="py-12 text-center text-heritage-umber dark:text-heritage-stone bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15">
            No knowledge generations created yet. Click "Trigger Build" to start ingestion.
          </div>
        ) : (
          generations.map((gen) => {
            const isActive = gen.id === activeGenId || gen.status === "ACTIVE";
            const isExpanded = expandedGenId === gen.id;

            return (
              <div
                key={gen.id}
                className={`bg-white dark:bg-heritage-carved-basalt rounded-xl border transition-all ${
                  isActive
                    ? "border-heritage-gold/40 shadow-md ring-1 ring-heritage-gold/20"
                    : "border-heritage-brown/10 dark:border-heritage-gold/15 shadow-xs"
                }`}
              >
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  {/* Generation Meta */}
                  <div className="flex items-start sm:items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-gold">
                      <Layers className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <h3 className="text-base font-bold text-heritage-brown dark:text-heritage-marble">
                          Generation #{gen.generation_number}
                        </h3>
                        {getStatusBadge(gen.status, isActive)}
                        <span className="text-xs text-heritage-umber dark:text-heritage-stone">
                          {gen.chunk_count} semantic chunks
                        </span>
                      </div>
                      <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1 font-mono">
                        Collection: {gen.chroma_collection_name}
                      </p>
                    </div>
                  </div>

                  {/* Actions & Timestamp */}
                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <span className="text-xs text-heritage-umber dark:text-heritage-stone hidden md:inline">
                      Created: {new Date(gen.created_at).toLocaleDateString()}
                    </span>

                    {/* Promote Button (if not already active and not building) */}
                    {!isActive && gen.status !== "FAILED" && canCurate && (
                      <button
                        onClick={() => handlePromote(gen.id)}
                        disabled={isPromoting === gen.id}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-heritage-gold/15 hover:bg-heritage-gold/25 text-heritage-brown dark:text-heritage-gold border border-heritage-gold/30 transition-colors disabled:opacity-50"
                      >
                        {isPromoting === gen.id ? "Promoting..." : "Promote to Active"}
                      </button>
                    )}

                    {/* Expand Pipeline Details */}
                    <button
                      onClick={() => setExpandedGenId(isExpanded ? null : gen.id)}
                      className="p-1.5 rounded-md text-heritage-umber dark:text-heritage-stone hover:text-heritage-brown dark:hover:text-heritage-marble"
                      aria-label="Toggle pipeline execution step details"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Stepper View */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-heritage-brown/5 dark:border-heritage-gold/10">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone mb-3">
                      Pipeline Execution Steps
                    </h4>
                    {gen.steps && gen.steps.length > 0 ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                        {gen.steps.map((s, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-stone-dark/50 border border-heritage-brown/5 dark:border-heritage-gold/10 text-xs"
                          >
                            <div className="flex items-center justify-between font-semibold text-heritage-brown dark:text-heritage-marble mb-1">
                              <span>{s.step}</span>
                              <span className="text-[10px] text-heritage-umber dark:text-heritage-stone">
                                {s.progress_pct}%
                              </span>
                            </div>
                            <span
                              className={`text-[10px] uppercase font-medium ${
                                s.status === "COMPLETED"
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : s.status === "FAILED"
                                  ? "text-heritage-terracotta"
                                  : "text-amber-600 dark:text-amber-400"
                              }`}
                            >
                              {s.status}
                            </span>
                            {s.error_message && (
                              <p className="mt-1 text-[10px] text-heritage-terracotta truncate" title={s.error_message}>
                                {s.error_message}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-heritage-umber dark:text-heritage-stone">
                        No individual step traces recorded for this generation.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Rollback Confirmation Modal */}
      {rollbackModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="rollback-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150"
        >
          <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/20 dark:border-heritage-gold/20 p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 text-amber-600 dark:text-heritage-gold mb-3">
              <RotateCcw className="w-6 h-6 flex-shrink-0" />
              <h3 id="rollback-modal-title" className="text-base font-bold">
                Instant Generation Rollback
              </h3>
            </div>
            <p className="text-xs text-heritage-umber dark:text-heritage-stone leading-relaxed mb-4">
              Select a prior immutable generation to reactivate. The active retrieval pointer switches atomically (&lt;100ms) without downtime.
            </p>

            <div className="mb-5">
              <label htmlFor="rollback-target" className="block text-xs font-semibold mb-1.5 text-heritage-brown dark:text-heritage-marble">
                Target Generation
              </label>
              <select
                id="rollback-target"
                value={rollbackTargetId}
                onChange={(e) => setRollbackTargetId(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
              >
                <option value="">-- Choose Target Generation --</option>
                {generations
                  .filter((g) => g.id !== activeGenId && g.status !== "FAILED")
                  .map((g) => (
                    <option key={g.id} value={g.id}>
                      Gen #{g.generation_number} ({g.chunk_count} chunks • {new Date(g.created_at).toLocaleDateString()})
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setRollbackModalOpen(false);
                  setRollbackTargetId("");
                }}
                disabled={isRollingBack}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble hover:border-heritage-gold border border-transparent transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRollback}
                disabled={isRollingBack || !rollbackTargetId}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-heritage-gold text-heritage-midnight-basalt hover:bg-heritage-gold-radiant shadow-xs transition-colors disabled:opacity-50"
              >
                {isRollingBack && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Confirm Rollback</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
