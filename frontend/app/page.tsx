"use client";

import { useState } from "react";
import { ShieldBackground } from "@/components/ShieldBackground";
import { analyzeQueryStream, submitFollowup, NodeEvent } from "@/lib/api";
import { ComplianceResponse } from "@/types/api";
import { motion, AnimatePresence } from "framer-motion";
import { Send, ShieldCheck, ShieldAlert, FileText, ChevronRight, AlertTriangle, Loader2, CheckCircle2, XCircle } from "lucide-react";
import clsx from "clsx";

// Node icon mapping for the pipeline visualization
const NODE_ICONS: Record<string, string> = {
  guardrail: "shield",
  retrieve: "search",
  clarify: "help",
  llm: "cpu",
  tool_executor: "wrench",
  validator: "check",
  semantic_override: "settings",
  governance: "scale",
  chat: "message",
  fallback: "alert",
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [result, setResult] = useState<ComplianceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeNodes, setActiveNodes] = useState<NodeEvent[]>([]);
  const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set());
  const [customText, setCustomText] = useState("");
  const [originalQuery, setOriginalQuery] = useState("");

  const handleAnalyze = async () => {
    if (!query.trim()) return;
    setIsThinking(true);
    setResult(null);
    setError(null);
    setActiveNodes([]);
    setSelectedOptions(new Set());
    setCustomText("");
    setOriginalQuery(query);

    try {
      const data = await analyzeQueryStream(
        query,
        (nodeEvent) => {
          setActiveNodes((prev) => [...prev, nodeEvent]);
        }
      );
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsThinking(false);
    }
  };

  const handleFollowup = async () => {
    setIsThinking(true);
    setResult(null);
    setError(null);
    setActiveNodes([]);

    const selected = Array.from(selectedOptions);

    try {
      const data = await submitFollowup(
        originalQuery,
        selected,
        customText,
        (nodeEvent) => {
          setActiveNodes((prev) => [...prev, nodeEvent]);
        }
      );
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsThinking(false);
    }
  };

  const toggleOption = (optionId: string) => {
    setSelectedOptions((prev) => {
      const next = new Set(prev);
      if (next.has(optionId)) next.delete(optionId);
      else next.add(optionId);
      return next;
    });
  };

  return (
    <main className="min-h-screen relative text-slate-100 font-sans selection:bg-cyan-500/30">
      <ShieldBackground />

      <div className="relative z-10 container mx-auto px-4 py-12 max-w-4xl flex flex-col min-h-screen">

        {/* Header */}
        <header className="flex items-center space-x-4 mb-16">
          <div className="w-12 h-12 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.5)]">
            <ShieldCheck className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-500">
              AGENTIC COMPLIANCE
            </h1>
            <p className="text-slate-400 text-sm tracking-widest uppercase">Autonomous Regulatory Oversight</p>
          </div>
        </header>

        {/* Chat Input */}
        <div className="flex-1 flex flex-col justify-center items-center transition-all duration-500 ease-in-out" style={{ justifyContent: result ? 'flex-start' : 'center' }}>

          <motion.div
            layout
            className="w-full bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl relative overflow-hidden group"
          >
            {/* Glowing Border Gradient */}
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-transparent to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe a compliance scenario (e.g., 'We lost patient data...')"
              className="w-full bg-transparent border-none outline-none text-lg resize-none placeholder:text-slate-600 h-24"
            />

            <div className="flex justify-between items-center mt-4 border-t border-slate-800 pt-4">
              <div className="flex space-x-2">
                {/* Capability Badges */}
                <span className="text-xs px-2 py-1 bg-slate-800 rounded-md text-slate-400 border border-slate-700">GDPR</span>
                <span className="text-xs px-2 py-1 bg-slate-800 rounded-md text-slate-400 border border-slate-700">CCPA</span>
                <span className="text-xs px-2 py-1 bg-slate-800 rounded-md text-slate-400 border border-slate-700">FDA</span>
              </div>

              <button
                onClick={handleAnalyze}
                disabled={isThinking || !query}
                className={clsx(
                  "flex items-center space-x-2 px-6 py-2 rounded-lg font-medium transition-all duration-300",
                  isThinking || !query
                    ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                    : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] text-white hover:scale-105"
                )}
              >
                <span>Analyze</span>
                <Send className="w-4 h-4" />
              </button>
            </div>
          </motion.div>

          <AnimatePresence>
            {isThinking && activeNodes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="mt-8 w-full"
              >
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-md">
                  <h3 className="text-cyan-400 text-sm font-bold uppercase tracking-wider mb-4 flex items-center">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Agent Pipeline — Live Execution
                  </h3>
                  <div className="space-y-2">
                    {activeNodes.map((node, i) => {
                      const isRetry = node.node === "llm" && node.retry_count > 0;
                      return (
                        <motion.div
                          key={`${node.node}-${i}`}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className={clsx(
                            "flex items-center space-x-3 px-4 py-2.5 rounded-lg border text-sm",
                            isRetry
                              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                              : "bg-slate-800/50 border-slate-700/50 text-slate-300"
                          )}
                        >
                          <span className="text-lg shrink-0">{NODE_ICONS[node.node] || "⚡"}</span>
                          <span className="font-mono text-xs text-slate-500 w-28 shrink-0">{node.node}</span>
                          <span className="flex-1">{node.label}</span>
                          {isRetry && (
                            <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full font-bold">
                              RETRY #{node.retry_count}
                            </span>
                          )}
                          <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                        </motion.div>
                      );
                    })}
                    {/* Pulsing current indicator */}
                    <motion.div
                      animate={{ opacity: [0.3, 0.8, 0.3] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="flex items-center space-x-3 px-4 py-2.5 rounded-lg border border-cyan-500/30 bg-cyan-500/5 text-cyan-400 text-sm"
                    >
                      <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                      <span>Awaiting next node...</span>
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            )}
            {isThinking && activeNodes.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="mt-8"
              >
                <div className="flex items-center space-x-2 text-cyan-400 text-sm font-mono">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <motion.span animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.5, repeat: Infinity }}>
                    CONNECTING TO AGENT PIPELINE...
                  </motion.span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Results Display */}
          <AnimatePresence>
            {result && !isThinking && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full mt-8 grid grid-cols-1 md:grid-cols-3 gap-6"
              >
                {/* Risk Card */}
                <div className="md:col-span-1">
                  <div className={clsx(
                    "h-full rounded-2xl p-6 border backdrop-blur-md flex flex-col items-center justify-center text-center transition-colors duration-500",
                    result.analysis.risk_level === "High" ? "bg-red-500/10 border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.2)]" :
                      result.analysis.risk_level === "Medium" ? "bg-amber-500/10 border-amber-500/50" :
                        result.analysis.risk_level === "Low" ? "bg-green-500/10 border-green-500/50" :
                          "bg-slate-800/50 border-slate-600/50 border-dashed"
                  )}>
                    <ShieldAlert className={clsx("w-16 h-16 mb-4",
                      result.analysis.risk_level === "High" ? "text-red-500" :
                        result.analysis.risk_level === "Medium" ? "text-amber-500" :
                          result.analysis.risk_level === "Low" ? "text-green-500" :
                            "text-slate-500"
                    )} />
                    <h3 className="text-xl font-bold uppercase tracking-widest text-slate-200">Risk Level</h3>
                    <p className={clsx("text-4xl font-black mt-2 bg-clip-text text-transparent",
                      result.analysis.risk_level === "High" ? "bg-gradient-to-b from-red-400 to-red-600" :
                        result.analysis.risk_level === "Medium" ? "bg-gradient-to-b from-amber-400 to-amber-600" :
                          result.analysis.risk_level === "Low" ? "bg-gradient-to-b from-green-400 to-green-600" :
                            "text-slate-400 text-3xl"
                    )}>{result.analysis.risk_level}</p>
                  </div>
                </div>

                {/* Analysis/Clarification Content */}
                <div className="md:col-span-2 space-y-6">
                  {/* Summary */}
                  <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-md">
                    <h3 className="text-cyan-400 text-sm font-bold uppercase tracking-wider mb-3 flex items-center">
                      <FileText className="w-4 h-4 mr-2" />
                      Executive Summary
                    </h3>
                    <p className="text-slate-300 leading-relaxed text-lg">
                      {result.analysis.summary}
                    </p>
                  </div>

                  {/* Clarification Options (Interactive) */}
                  {result.decision === "CLARIFICATION_REQUIRED" && result.clarification && (
                    <div className="bg-slate-900/40 border border-amber-500/50 rounded-2xl p-6 backdrop-blur-md shadow-[0_0_20px_rgba(245,158,11,0.1)]">
                      <h3 className="text-amber-400 text-sm font-bold uppercase tracking-wider mb-2 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-2" />
                        Clarification Needed
                      </h3>
                      <p className="text-slate-300 mb-5 text-sm">{result.clarification.summary}</p>
                      <div className="space-y-3">
                        {result.clarification.options.map((option) => (
                          <button
                            key={option.id}
                            onClick={() => {
                              if (option.id === "opt_unknown") {
                                // Skip clarification — re-run without selections
                                setSelectedOptions(new Set(["I don't know the details"]));
                                setTimeout(() => handleFollowup(), 100);
                                return;
                              }
                              toggleOption(option.text);
                            }}
                            className={clsx(
                              "w-full flex items-start p-4 rounded-xl border transition-all duration-200 text-left",
                              option.id === "opt_custom"
                                ? "border-slate-600/50 bg-slate-800/30 cursor-default"
                                : selectedOptions.has(option.text)
                                  ? "border-cyan-500/70 bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.15)]"
                                  : "border-slate-700/50 bg-slate-800/30 hover:border-slate-600 hover:bg-slate-800/50"
                            )}
                          >
                            <span className={clsx(
                              "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-0.5 transition-colors",
                              option.id === "opt_unknown"
                                ? "bg-slate-700 text-slate-400"
                                : option.id === "opt_custom"
                                  ? "bg-blue-500/20 text-blue-400"
                                  : selectedOptions.has(option.text)
                                    ? "bg-cyan-500 text-white"
                                    : "bg-amber-500/20 text-amber-500"
                            )}>
                              {option.id === "opt_unknown" ? "?" : option.id === "opt_custom" ? "✎" : option.rank}
                            </span>
                            <div className="flex-1">
                              <p className="text-slate-200">{option.text}</p>
                              {option.id === "opt_custom" && (
                                <textarea
                                  value={customText}
                                  onChange={(e) => setCustomText(e.target.value)}
                                  placeholder="Describe your specific situation..."
                                  className="mt-2 w-full bg-slate-900/60 border border-slate-700/50 rounded-lg p-3 text-sm text-slate-300 placeholder:text-slate-600 outline-none focus:border-cyan-500/50 resize-none h-20"
                                  onClick={(e) => e.stopPropagation()}
                                />
                              )}
                            </div>
                          </button>
                        ))}
                      </div>

                      {/* Submit Button */}
                      <button
                        onClick={handleFollowup}
                        disabled={selectedOptions.size === 0 && !customText.trim()}
                        className={clsx(
                          "mt-5 w-full py-3 rounded-xl font-semibold text-sm uppercase tracking-wider transition-all duration-300",
                          selectedOptions.size > 0 || customText.trim()
                            ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)]"
                            : "bg-slate-800 text-slate-500 cursor-not-allowed"
                        )}
                      >
                        Analyze with Context →
                      </button>
                    </div>
                  )}

                  {/* Clarification Precondition Matrix (legacy) */}
                  {result.decision === "CLARIFICATION_REQUIRED" && !result.clarification && result.analysis.needs_clarification && (
                    <div className="bg-slate-900/40 border border-amber-500/50 rounded-2xl p-6 backdrop-blur-md shadow-[0_0_20px_rgba(245,158,11,0.1)]">
                      <h3 className="text-amber-400 text-sm font-bold uppercase tracking-wider mb-4 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-2" />
                        Missing Preconditions Detected
                      </h3>
                      <p className="text-slate-400 mb-4 text-sm">To provide a confident regulatory assessment, the system requires the following information:</p>
                      <div className="space-y-3">
                        {result.analysis.missing_preconditions.map((question, i) => (
                          <div key={i} className="flex items-start p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/20 text-amber-500 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">{i + 1}</span>
                            <p className="text-slate-200">{question}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Reasoning Map */}
                  {result.decision !== "CLARIFICATION_REQUIRED" && (
                    <div className="bg-slate-900/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-md">
                      <h3 className="text-blue-400 text-sm font-bold uppercase tracking-wider mb-4">
                        Regulatory Analysis
                      </h3>
                      <div className="space-y-4">
                        {result.analysis.reasoning_map?.map((item, i) => (
                          <div key={i} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50 hover:border-cyan-500/30 transition-colors">
                            <div className="flex justify-between items-start mb-2">
                              <span className="text-slate-400 text-sm">Fact detected:</span>
                              <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded font-mono">
                                {item.regulation} {item.article}
                              </span>
                            </div>
                            <p className="text-white font-medium mb-2">"{item.fact}"</p>
                            <div className="flex items-start text-sm text-slate-400">
                              <ChevronRight className="w-4 h-4 mr-1 text-cyan-500 mt-0.5 shrink-0" />
                              <p>{item.justification}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>
    </main>
  );
}
