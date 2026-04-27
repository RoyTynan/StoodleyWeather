'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import type { PromptDetail } from '@/lib/db';

export default function PromptDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [prompt, setPrompt] = useState<PromptDetail | null>(null);
  const [error, setError] = useState(false);
  const [showEnriched, setShowEnriched] = useState(false);

  useEffect(() => {
    fetch(`/api/prompts/${id}`)
      .then((r) => {
        if (!r.ok) { setError(true); return null; }
        return r.json();
      })
      .then((data) => data && setPrompt(data));
  }, [id]);

  if (error) return (
    <div className="p-6">
      <Link href="/" className="text-blue-400 hover:underline text-sm">← Back</Link>
      <p className="mt-4 text-red-400">Prompt not found.</p>
    </div>
  );

  if (!prompt) return (
    <div className="p-6 text-gray-600">Loading…</div>
  );

  const enrichedDiffers = prompt.enriched_message !== prompt.raw_query;

  return (
    <div className="p-6 max-w-screen-xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <Link href="/" className="text-blue-400 hover:underline text-sm">← Back</Link>
        <h1 className="text-lg font-bold">Prompt #{prompt.id}</h1>
        <span className="text-gray-500 text-sm font-mono">{new Date(prompt.timestamp).toLocaleString()}</span>
        {prompt.repo && (
          <span className="bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded text-xs font-mono">{prompt.repo}</span>
        )}
        {prompt.latency_ms != null && (
          <span className="text-gray-500 text-sm font-mono">{(prompt.latency_ms / 1000).toFixed(1)}s</span>
        )}
        <div className="flex gap-1">
          {!!prompt.skeleton_injected && <span className="bg-purple-950 text-purple-300 border border-purple-800 px-1.5 py-0.5 rounded text-xs">skel</span>}
          {!!prompt.chunks_injected && <span className="bg-green-950 text-green-300 border border-green-800 px-1.5 py-0.5 rounded text-xs">chunks</span>}
          {!!prompt.verify_injected && <span className="bg-yellow-950 text-yellow-300 border border-yellow-800 px-1.5 py-0.5 rounded text-xs">verify</span>}
        </div>
      </div>

      {/* INPUT / OUTPUT panels */}
      <div className="grid grid-cols-2 gap-4 mb-4">

        {/* INPUT */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold text-blue-400 uppercase tracking-widest">Input — User Prompt</h2>
            {enrichedDiffers && (
              <button
                onClick={() => setShowEnriched(!showEnriched)}
                className="text-xs text-purple-400 hover:underline"
              >
                {showEnriched ? 'Show original' : 'Show enriched'}
              </button>
            )}
          </div>
          <pre className="flex-1 bg-blue-950 border border-blue-900 rounded p-3 text-xs font-mono text-blue-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[70vh]">
            {showEnriched && enrichedDiffers
              ? (prompt.enriched_message ?? '—')
              : (prompt.raw_query ?? '—')}
          </pre>
        </div>

        {/* OUTPUT */}
        <div className="flex flex-col">
          <h2 className="text-xs font-semibold text-green-400 uppercase tracking-widest mb-2">Output — LLM Response</h2>
          <pre className="flex-1 bg-green-950 border border-green-900 rounded p-3 text-xs font-mono text-green-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[70vh]">
            {prompt.response_text ?? '— not yet captured (restart proxy to enable)'}
          </pre>
        </div>

      </div>
    </div>
  );
}
