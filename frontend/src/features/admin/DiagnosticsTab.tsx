import React, { useState } from "react";
import {
  Search,
  Cpu,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { adminApiClient } from "@/services/adminApi";
import { RetrievalDiagnosticResponse, RetrievalCandidate } from "@/types/api";

export const DiagnosticsTab: React.FC = () => {
  const [query, setQuery] = useState<string>("Who built the Chennakeshava Temple and when?");
  const [topDense, setTopDense] = useState<number>(15);
  const [topSparse, setTopSparse] = useState<number>(15);
  const [topFused, setTopFused] = useState<number>(10);
  const [topFinal, setTopFinal] = useState<number>(4);
  const [threshold, setThreshold] = useState<number>(0.35);

  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [result, setResult] = useState<RetrievalDiagnosticResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<"final" | "reranked" | "fused" | "dense" | "sparse">("final");

  const handleRunDiagnostic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsRunning(true);
    setErrorMessage(null);
    try {
      const data = await adminApiClient.runRetrievalDiagnostics({
        query: query.trim(),
        top_dense: topDense,
        top_sparse: topSparse,
        top_fused: topFused,
        top_final: topFinal,
        score_threshold: threshold,
      });
      setResult(data);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to execute retrieval diagnostic pipeline.");
    } finally {
      setIsRunning(false);
    }
  };

  const renderCandidateCard = (c: RetrievalCandidate, idx: number) => {
    return (
      <div
        key={`${c.chunk_id}-${idx}`}
        className="p-3.5 rounded-lg bg-heritage-sandstone/50 dark:bg-heritage-stone-dark/50 border border-heritage-brown/10 dark:border-heritage-gold/10 text-xs space-y-2"
      >
        <div className="flex items-center justify-between flex-wrap gap-1 font-semibold text-heritage-brown dark:text-heritage-marble">
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 rounded bg-heritage-gold/20 text-heritage-brown dark:text-heritage-gold text-[10px]">
              #{idx + 1}
            </span>
            <span className="truncate max-w-[200px]" title={c.chunk_id}>
              {c.chunk_id}
            </span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-heritage-umber dark:text-heritage-stone">
            <span>Page {c.page_number}</span>
            {c.section_heading && <span className="font-medium">• {c.section_heading}</span>}
          </div>
        </div>

        {/* Scores Matrix */}
        <div className="flex items-center gap-3 text-[11px] font-mono text-heritage-umber dark:text-heritage-stone bg-white/60 dark:bg-heritage-carved-basalt/60 px-2.5 py-1 rounded">
          {c.dense_score !== null && c.dense_score !== undefined && (
            <span>Dense: {c.dense_score.toFixed(4)} (Rank {c.dense_rank})</span>
          )}
          {c.sparse_score !== null && c.sparse_score !== undefined && (
            <span>Sparse: {c.sparse_score.toFixed(2)} (Rank {c.sparse_rank})</span>
          )}
          {c.rrf_score !== undefined && (
            <span>RRF: {c.rrf_score.toFixed(4)}</span>
          )}
          {c.rerank_score !== null && c.rerank_score !== undefined && (
            <span className={c.is_selected ? "text-emerald-600 dark:text-emerald-400 font-bold" : ""}>
              Cross-Encoder: {c.rerank_score.toFixed(4)}
            </span>
          )}
          {c.is_selected && (
            <span className="ml-auto px-1.5 py-0.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold rounded text-[10px]">
              PASSED CUTOFF
            </span>
          )}
        </div>

        <p className="text-heritage-brown/90 dark:text-heritage-marble/90 line-clamp-3 leading-relaxed">
          {c.content}
        </p>
      </div>
    );
  };

  const getStageCandidates = (): RetrievalCandidate[] => {
    if (!result) return [];
    switch (activeStage) {
      case "final":
        return result.final_chunks;
      case "reranked":
        return result.reranked_candidates;
      case "fused":
        return result.fused_candidates;
      case "dense":
        return result.dense_candidates;
      case "sparse":
        return result.sparse_candidates;
      default:
        return [];
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
        <h2 className="text-xl font-bold font-display text-heritage-brown dark:text-heritage-marble">
          Hybrid RAG Retrieval Diagnostics
        </h2>
        <p className="text-xs text-heritage-umber dark:text-heritage-stone mt-1">
          Inspect intermediate candidate sets across ChromaDB dense vector search, BM25 lexical search, RRF fusion, and Cross-Encoder re-ranking.
        </p>
      </div>

      {/* Query Form */}
      <form onSubmit={handleRunDiagnostic} className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 p-5 shadow-xs space-y-4">
        <div>
          <label htmlFor="diag-query" className="block text-xs font-semibold uppercase tracking-wider text-heritage-brown dark:text-heritage-marble mb-1.5">
            Probe Search Query
          </label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-heritage-umber dark:text-heritage-stone" />
            <input
              id="diag-query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Queen Shantala Devi, Darpana Sundari, lathe turned pillars..."
              required
              disabled={isRunning}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble focus:outline-hidden focus:ring-2 focus:ring-heritage-gold"
            />
          </div>
        </div>

        {/* Hyperparameter Controls */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
          <div>
            <label className="block text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1">
              Top Dense: {topDense}
            </label>
            <input
              type="number"
              min={1}
              max={50}
              value={topDense}
              onChange={(e) => setTopDense(Number(e.target.value))}
              className="w-full px-2 py-1 text-xs rounded border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1">
              Top Sparse: {topSparse}
            </label>
            <input
              type="number"
              min={1}
              max={50}
              value={topSparse}
              onChange={(e) => setTopSparse(Number(e.target.value))}
              className="w-full px-2 py-1 text-xs rounded border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1">
              Top Fused: {topFused}
            </label>
            <input
              type="number"
              min={1}
              max={30}
              value={topFused}
              onChange={(e) => setTopFused(Number(e.target.value))}
              className="w-full px-2 py-1 text-xs rounded border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1">
              Top Final: {topFinal}
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={topFinal}
              onChange={(e) => setTopFinal(Number(e.target.value))}
              className="w-full px-2 py-1 text-xs rounded border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-heritage-umber dark:text-heritage-stone mb-1">
              Threshold: {threshold}
            </label>
            <input
              type="number"
              step={0.05}
              min={0.0}
              max={1.0}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full px-2 py-1 text-xs rounded border border-heritage-brown/20 dark:border-heritage-gold/20 bg-heritage-ivory dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isRunning}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-midnight-basalt shadow-xs disabled:opacity-50 transition-colors"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Executing Pipeline Probe...</span>
              </>
            ) : (
              <>
                <Cpu className="w-3.5 h-3.5" />
                <span>Execute Diagnostic Probe</span>
              </>
            )}
          </button>
        </div>
      </form>

      {errorMessage && (
        <div
          role="alert"
          className="p-3 rounded-lg bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300 text-xs flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Results Viewport */}
      {result && (
        <div className="space-y-5">
          {/* Telemetry Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 rounded-lg bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15">
              <span className="text-[10px] uppercase font-bold text-heritage-umber dark:text-heritage-stone block">
                Active Generation
              </span>
              <span className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
                Gen #{result.generation_number}
              </span>
            </div>

            {Object.entries(result.latency_breakdown_ms || {}).map(([stage, ms]) => (
              <div
                key={stage}
                className="p-3 rounded-lg bg-white dark:bg-heritage-carved-basalt border border-heritage-brown/10 dark:border-heritage-gold/15"
              >
                <span className="text-[10px] uppercase font-bold text-heritage-umber dark:text-heritage-stone block truncate" title={stage}>
                  {stage.replace("_ms", "")}
                </span>
                <span className="text-sm font-bold text-heritage-brown dark:text-heritage-marble">
                  {ms.toFixed(1)} ms
                </span>
              </div>
            ))}
          </div>

          {/* Pipeline Stage Tabs */}
          <div className="bg-white dark:bg-heritage-carved-basalt rounded-xl border border-heritage-brown/10 dark:border-heritage-gold/15 p-5 shadow-xs">
            <div className="flex items-center gap-2 overflow-x-auto pb-3 mb-4 border-b border-heritage-brown/10 dark:border-heritage-gold/15">
              <button
                onClick={() => setActiveStage("final")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  activeStage === "final"
                    ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                    : "bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
                }`}
              >
                Final Chunks ({result.final_chunks.length})
              </button>

              <button
                onClick={() => setActiveStage("reranked")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  activeStage === "reranked"
                    ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                    : "bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
                }`}
              >
                Re-ranked ({result.reranked_candidates.length})
              </button>

              <button
                onClick={() => setActiveStage("fused")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  activeStage === "fused"
                    ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                    : "bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
                }`}
              >
                RRF Fused ({result.fused_candidates.length})
              </button>

              <button
                onClick={() => setActiveStage("dense")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  activeStage === "dense"
                    ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                    : "bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
                }`}
              >
                Dense Chroma ({result.dense_candidates.length})
              </button>

              <button
                onClick={() => setActiveStage("sparse")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  activeStage === "sparse"
                    ? "bg-heritage-gold text-heritage-midnight-basalt shadow-xs"
                    : "bg-heritage-sandstone dark:bg-heritage-stone-dark text-heritage-brown dark:text-heritage-marble"
                }`}
              >
                Sparse BM25 ({result.sparse_candidates.length})
              </button>
            </div>

            {/* Candidates List */}
            <div className="space-y-3">
              {getStageCandidates().length === 0 ? (
                <p className="text-xs text-heritage-umber dark:text-heritage-stone py-4 text-center">
                  No candidates at this stage.
                </p>
              ) : (
                getStageCandidates().map((c, idx) => renderCandidateCard(c, idx))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
