'use client';

import React, { useEffect, useState } from 'react';
import type { PromptSummary, PromptDetail } from '@/lib/db';

export default function HomePage() {
  const PAGE_SIZE = 25;
  const [prompts, setPrompts] = useState<PromptSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<PromptDetail | null>(null);
  const [showEnriched, setShowEnriched] = useState(false);
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const fetchPrompts = async (p = page) => {
    const res = await fetch(`/api/prompts?limit=${PAGE_SIZE}&offset=${p * PAGE_SIZE}`);
    const data = await res.json();
    setPrompts(data.prompts);
    setTotal(data.total);
    setLastRefresh(new Date());
  };

  useEffect(() => {
    fetchPrompts(page);
    const interval = setInterval(() => fetchPrompts(page), 10_000);
    return () => clearInterval(interval);
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const goToPage = (p: number) => {
    setPage(p);
    setExpandedId(null);
    setDetail(null);
  };

  const handleExpand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(id);
    setDetail(null);
    setShowEnriched(false);
    const res = await fetch(`/api/prompts/${id}`);
    const data = await res.json();
    setDetail(data);
  };

  const handleDeleteAll = async () => {
    await fetch('/api/prompts', { method: 'DELETE' });
    setShowDeleteAllModal(false);
    setExpandedId(null);
    setDetail(null);
    setPage(0);
    fetchPrompts(0);
  };

  const handleDeleteRow = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (pendingDeleteId !== id) {
      setPendingDeleteId(id);
      return;
    }
    await fetch(`/api/prompts/${id}`, { method: 'DELETE' });
    setPendingDeleteId(null);
    if (expandedId === id) { setExpandedId(null); setDetail(null); }
    fetchPrompts(page);
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold tracking-tight">LLM Prompt Monitor</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            {total} prompts{lastRefresh && ` · refreshed ${lastRefresh.toLocaleTimeString()}`}
          </span>
          <button
            onClick={() => setShowDeleteAllModal(true)}
            className="px-3 py-1 rounded text-xs bg-red-950 text-red-400 border border-red-800 hover:bg-red-900 transition-colors"
          >
            Delete All
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-800">
              <th className="pb-2 pr-4 font-medium">ID</th>
              <th className="pb-2 pr-4 font-medium">Time</th>
              <th className="pb-2 pr-4 font-medium">Repo</th>
              <th className="pb-2 pr-4 font-medium">Model</th>
              <th className="pb-2 pr-4 font-medium w-1/3">Query</th>
              <th className="pb-2 pr-4 font-medium">Context</th>
              <th className="pb-2 pr-4 font-medium">Size</th>
              <th className="pb-2 pr-4 font-medium">Latency</th>
              <th className="pb-2 pr-4 font-medium">Finish</th>
              <th className="pb-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {prompts.map((p) => (
              <React.Fragment key={p.id}>
                <tr className="border-b border-gray-900 hover:bg-gray-900 transition-colors cursor-pointer"
                    onClick={() => handleExpand(p.id)}>
                  <td className="py-2 pr-4 text-blue-400 font-mono">#{p.id}</td>
                  <td className="py-2 pr-4 text-gray-500 whitespace-nowrap font-mono text-xs">
                    {new Date(p.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="py-2 pr-4">
                    {p.repo ? (
                      <span className="bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded text-xs font-mono">
                        {p.repo}
                      </span>
                    ) : (
                      <span className="text-gray-700">—</span>
                    )}
                  </td>
                  <td className="py-2 pr-4">
                    {p.model ? (
                      <span className="bg-gray-900 text-gray-300 border border-gray-700 px-2 py-0.5 rounded text-xs font-mono whitespace-nowrap" title={p.model}>
                        {p.model.split('/').pop()?.replace(/\.gguf$/i, '').slice(0, 28) ?? p.model}
                      </span>
                    ) : (
                      <span className="text-gray-700">—</span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-gray-400 max-w-xs">
                    <span className="block truncate text-blue-300">
                      {p.raw_query?.slice(0, 100) ?? '—'}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <div className="flex gap-1 flex-wrap">
                      {!!p.skeleton_injected && <span className="bg-purple-950 text-purple-300 border border-purple-800 px-1.5 py-0.5 rounded text-xs">skel</span>}
                      {!!p.chunks_injected && <span className="bg-green-950 text-green-300 border border-green-800 px-1.5 py-0.5 rounded text-xs">chunks</span>}
                      {!!p.verify_injected && <span className="bg-yellow-950 text-yellow-300 border border-yellow-800 px-1.5 py-0.5 rounded text-xs">verify</span>}
                    </div>
                  </td>
                  <td className="py-2 pr-4 text-gray-500 font-mono text-xs whitespace-nowrap">
                    {(p.msg_size / 1024).toFixed(0)} KB
                  </td>
                  <td className="py-2 pr-4 text-gray-500 font-mono text-xs whitespace-nowrap">
                    {p.latency_ms != null ? `${(p.latency_ms / 1000).toFixed(1)}s` : '—'}
                  </td>
                  <td className="py-2 pr-4 text-gray-600 text-xs font-mono">
                    {p.finish_reason ?? 'stream'}
                  </td>
                  <td className="py-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDeleteRow(e, p.id)}
                      onBlur={() => setPendingDeleteId(null)}
                      className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                        pendingDeleteId === p.id
                          ? 'bg-red-700 text-white border border-red-500 hover:bg-red-600'
                          : 'bg-transparent text-gray-700 border border-gray-800 hover:text-red-400 hover:border-red-800'
                      }`}
                    >
                      {pendingDeleteId === p.id ? 'Sure?' : '✕'}
                    </button>
                  </td>
                </tr>

                {expandedId === p.id && (
                  <tr className="border-b border-gray-700">
                    <td colSpan={10} className="px-2 py-3 bg-gray-950">
                      {!detail ? (
                        <div className="text-gray-600 text-xs py-2">Loading…</div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          {/* Input */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">Input</span>
                              {detail.enriched_message !== detail.raw_query && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); setShowEnriched(!showEnriched); }}
                                  className="text-xs text-purple-400 hover:underline"
                                >
                                  {showEnriched ? 'Show original' : 'Show enriched'}
                                </button>
                              )}
                            </div>
                            <pre className="bg-blue-950 border border-blue-900 rounded p-3 text-xs font-mono text-blue-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[60vh]">
                              {showEnriched && detail.enriched_message !== detail.raw_query
                                ? (detail.enriched_message ?? '—')
                                : (detail.raw_query ?? '—')}
                            </pre>
                          </div>
                          {/* Output */}
                          <div>
                            <span className="text-xs font-semibold text-green-400 uppercase tracking-widest block mb-1">Output</span>
                            <pre className="bg-green-950 border border-green-900 rounded p-3 text-xs font-mono text-green-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[60vh]">
                              {detail.response_text ?? '— not captured'}
                            </pre>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {prompts.length === 0 && (
          <div className="text-center text-gray-600 py-12">No prompts logged yet.</div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <button
            onClick={() => goToPage(page - 1)}
            disabled={page === 0}
            className="px-3 py-1 rounded bg-gray-900 hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="font-mono">Page {page + 1} of {totalPages}</span>
          <button
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 rounded bg-gray-900 hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}

      {/* Delete All modal */}
      {showDeleteAllModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
            <h2 className="text-base font-bold text-white mb-2">Delete all logs?</h2>
            <p className="text-sm text-gray-400 mb-6">
              This will permanently delete all {total} prompt records. This cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteAllModal(false)}
                className="px-4 py-2 rounded text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAll}
                className="px-4 py-2 rounded text-sm bg-red-700 text-white hover:bg-red-600 transition-colors font-semibold"
              >
                Delete all
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
