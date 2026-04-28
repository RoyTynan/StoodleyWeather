'use client';

import React, { useEffect, useState } from 'react';
import type { TaskGroup, TaskStep, PromptDetail } from '@/lib/db';

// ── Step type styling ────────────────────────────────────────────────────────

const STEP_STYLE: Record<string, { badge: string; row: string }> = {
  TASK:     { badge: 'bg-gray-700 text-gray-100 border-gray-500',      row: 'border-gray-800' },
  READ:     { badge: 'bg-gray-900 text-gray-400 border-gray-700',      row: 'border-gray-900' },
  WRITE:    { badge: 'bg-purple-950 text-purple-300 border-purple-800', row: 'border-purple-950' },
  CMD:      { badge: 'bg-yellow-950 text-yellow-300 border-yellow-800', row: 'border-yellow-950' },
  ERROR:    { badge: 'bg-red-950 text-red-400 border-red-800',          row: 'border-red-950' },
  HALT:     { badge: 'bg-red-600 text-white border-red-400',            row: 'border-red-600' },
  DONE:     { badge: 'bg-teal-950 text-teal-300 border-teal-800',       row: 'border-teal-950' },
  FOLLOWUP: { badge: 'bg-orange-950 text-orange-300 border-orange-800', row: 'border-orange-950' },
  TOOL:     { badge: 'bg-gray-900 text-gray-500 border-gray-800',      row: 'border-gray-900' },
  PROMPT:   { badge: 'bg-blue-950 text-blue-300 border-blue-900',      row: 'border-blue-900' },
};

function stepStyle(type: string | null) {
  return STEP_STYLE[type ?? ''] ?? STEP_STYLE.TOOL;
}

const STEP_DESC: Record<string, string> = {
  TASK:     'Opening prompt — the user\'s typed task. Starts a new task group and assigns a task ID.',
  READ:     'Cline read a file via read_repo_file. Enrichment is skipped; Cline reads the file directly from the MCP server.',
  WRITE:    'Cline wrote or edited a file. Triggers automatic verification and dependency impact analysis on the next step.',
  CMD:      'Cline ran a shell command via execute_command.',
  ERROR:    'The LLM returned an error, an invalid response, or the proxy could not reach the LLM server.',
  HALT:     'Context window saturation detected — the LLM returned an empty response. The proxy sent an attempt_completion to stop Cline and block retries.',
  DONE:     'Task completed — Cline issued attempt_completion successfully.',
  FOLLOWUP: 'A follow-up user message within the same task, after the initial TASK step.',
  TOOL:     'An MCP tool call (semantic search, verify_project, etc.) that does not match a more specific step type.',
  PROMPT:   'A prompt that does not match any other step type classification.',
};

// ── Small reusable bits ──────────────────────────────────────────────────────

function StepBadge({ type }: { type: string | null }) {
  const s = stepStyle(type);
  return (
    <span className={`px-1.5 py-0.5 rounded text-base font-mono border ${s.badge} shrink-0 w-20 text-center`}>
      {type ?? '—'}
    </span>
  );
}

function ContextBadges({ step }: { step: TaskStep }) {
  return (
    <div className="flex gap-1 shrink-0">
      {!!step.skeleton_injected && <span className="bg-purple-950 text-purple-300 border border-purple-800 px-1 py-0.5 rounded text-base">skel</span>}
      {!!step.chunks_injected   && <span className="bg-green-950 text-green-300 border border-green-800 px-1 py-0.5 rounded text-base">chunks</span>}
      {!!step.verify_injected   && <span className="bg-yellow-950 text-yellow-300 border border-yellow-800 px-1 py-0.5 rounded text-base">verify</span>}
    </div>
  );
}

function ModelBadge({ model }: { model: string | null }) {
  if (!model) return null;
  const label = model.split('/').pop()?.replace(/\.gguf$/i, '').slice(0, 24) ?? model;
  return (
    <span className="bg-gray-900 text-gray-400 border border-gray-700 px-1.5 py-0.5 rounded text-base font-mono shrink-0" title={model}>
      {label}
    </span>
  );
}

// ── Step row ─────────────────────────────────────────────────────────────────

function StepRow({ step }: { step: TaskStep }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<PromptDetail | null>(null);
  const [showEnriched, setShowEnriched] = useState(false);
  const s = stepStyle(step.step_type);

  const handleExpand = async () => {
    if (!expanded && !detail) {
      const res = await fetch(`/api/prompts/${step.id}`);
      if (res.ok) setDetail(await res.json());
    }
    setExpanded(!expanded);
  };

  const preview = (() => {
    const q = step.raw_query ?? '';
    // Extract filename from tool result messages like [read_file for 'src/foo.ts']
    const fileMatch = q.match(/\[\w+(?:_\w+)* for ['"]([^'"]+)['"]/);
    if (fileMatch) return fileMatch[1];
    // Extract command from [execute_command] blocks
    const cmdMatch = q.match(/Command:\s*(.+?)(?:\n|$)/);
    if (cmdMatch) return cmdMatch[1].trim().slice(0, 120);
    // For TASK steps show the clean typed prompt
    if (step.user_task) return step.user_task.replace(/\s+/g, ' ').slice(0, 120);
    return q.replace(/\s+/g, ' ').slice(0, 120);
  })();

  return (
    <div className={`border-b last:border-b-0 ${s.row}`}>
      <div
        className="flex items-center gap-3 px-4 py-2 cursor-pointer hover:bg-gray-950 transition-colors"
        onClick={handleExpand}
      >
        <StepBadge type={step.step_type} />
        <span className="text-base text-gray-600 font-mono w-14 shrink-0 text-right">
          {step.latency_ms != null ? `${(step.latency_ms / 1000).toFixed(1)}s` : '—'}
        </span>
        <span className="text-base text-gray-500 truncate flex-1">{preview || '—'}</span>
        <ContextBadges step={step} />
        {(step.prompt_tokens != null || step.completion_tokens != null) && (
          <span className="text-base text-gray-600 font-mono shrink-0 whitespace-nowrap">
            {step.prompt_tokens ?? '?'}↑ {step.completion_tokens ?? '?'}↓
          </span>
        )}
        <ModelBadge model={step.model} />
        <span className="text-base text-gray-700 font-mono shrink-0">#{step.id}</span>
      </div>

      {expanded && (
        <div className="px-4 pb-3 pt-1">
          {!detail ? (
            <div className="text-base text-gray-600 py-2">Loading…</div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-base font-semibold text-blue-400 uppercase tracking-widest">Input</span>
                  {detail.enriched_message !== detail.raw_query && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setShowEnriched(!showEnriched); }}
                      className="text-base text-purple-400 hover:underline"
                    >
                      {showEnriched ? 'Show original' : 'Show enriched'}
                    </button>
                  )}
                </div>
                <pre className="bg-blue-950 border border-blue-900 rounded p-3 text-base font-mono text-blue-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[50vh]">
                  {showEnriched && detail.enriched_message !== detail.raw_query
                    ? (detail.enriched_message ?? '—')
                    : (detail.raw_query ?? '—')}
                </pre>
              </div>
              <div>
                <span className="text-base font-semibold text-green-400 uppercase tracking-widest block mb-1">Output</span>
                <pre className="bg-green-950 border border-green-900 rounded p-3 text-base font-mono text-green-100 whitespace-pre-wrap leading-relaxed overflow-y-auto max-h-[50vh]">
                  {detail.response_text ?? '— not captured'}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Task card ─────────────────────────────────────────────────────────────────

function TaskCard({
  task,
  onDeleted,
}: {
  task: TaskGroup;
  onDeleted: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(false);

  const totalSec = task.total_latency_ms != null
    ? (task.total_latency_ms / 1000).toFixed(1) + 's'
    : '—';

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!pendingDelete) { setPendingDelete(true); return; }
    await fetch(`/api/tasks/${task.task_id}`, { method: 'DELETE' });
    onDeleted();
  };

  return (
    <div className="border border-gray-800 rounded mb-2 overflow-hidden">
      {/* Card header */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-900 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="text-gray-400 text-base shrink-0">{expanded ? '▾' : '▸'}</span>

        <span className="text-gray-200 text-base flex-1 truncate" title={task.user_task ?? undefined}>
          {task.user_task ?? <span className="text-gray-600 italic">no task text</span>}
        </span>

        {task.repo && (
          <span className="bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded text-base font-mono shrink-0">
            {task.repo}
          </span>
        )}

        <span className="text-base text-gray-600 font-mono shrink-0">{task.step_count} steps</span>
        <span className="text-base text-gray-600 font-mono shrink-0">{totalSec}</span>
        <span className="text-base text-gray-500 font-mono shrink-0">
          {new Date(task.started_at).toLocaleString()}
        </span>

        <button
          onClick={handleDelete}
          onBlur={() => setPendingDelete(false)}
          className={`px-2 py-0.5 rounded text-base font-mono transition-colors shrink-0 ${
            pendingDelete
              ? 'bg-red-700 text-white border border-red-500 hover:bg-red-600'
              : 'bg-transparent text-gray-700 border border-gray-800 hover:text-red-400 hover:border-red-800'
          }`}
        >
          {pendingDelete ? 'Sure?' : '✕'}
        </button>
      </div>

      {/* Step timeline */}
      {expanded && (
        <div className="border-t border-gray-800 bg-gray-950">
          {task.steps.map(step => (
            <StepRow key={step.id} step={step} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function HomePage() {
  const PAGE_SIZE = 10;
  const [tasks, setTasks] = useState<TaskGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [activeLegend, setActiveLegend] = useState<string | null>(null);
  const [config, setConfig] = useState<{ timestamp: string; config: Record<string, string | number> } | null>(null);

  const fetchTasks = async (p = page) => {
    const res = await fetch(`/api/tasks?limit=${PAGE_SIZE}&offset=${p * PAGE_SIZE}`);
    const data = await res.json();
    setTasks(data.tasks);
    setTotal(data.total);
    setLastRefresh(new Date());
  };

  useEffect(() => {
    fetchTasks(page);
    const interval = setInterval(() => fetchTasks(page), 10_000);
    return () => clearInterval(interval);
  }, [page]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const goToPage = (p: number) => setPage(p);

  const handleShowConfig = async () => {
    if (!showConfig && !config) {
      const res = await fetch('/api/config');
      if (res.ok) setConfig(await res.json());
    }
    setShowConfig(!showConfig);
  };

  const handleDeleteAll = async () => {
    await fetch('/api/tasks', { method: 'DELETE' });
    setShowDeleteAllModal(false);
    setPage(0);
    fetchTasks(0);
  };

  return (
    <div className="p-6 max-w-screen-xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight">LLM Prompt Monitor</h1>
        <div className="flex items-center gap-4">
          <span className="text-base text-gray-500">
            {total} tasks{lastRefresh && ` · refreshed ${lastRefresh.toLocaleTimeString()}`}
          </span>
          <button
            onClick={handleShowConfig}
            className="px-3 py-1 rounded text-base bg-gray-900 text-gray-400 border border-gray-700 hover:bg-gray-800 transition-colors"
          >
            {showConfig ? 'Hide Config' : 'Config'}
          </button>
          <button
            onClick={() => setShowDeleteAllModal(true)}
            className="px-3 py-1 rounded text-base bg-red-950 text-red-400 border border-red-800 hover:bg-red-900 transition-colors"
          >
            Delete All
          </button>
        </div>
      </div>

      {/* Config panel */}
      {showConfig && (
        <div className="mb-6 border border-gray-800 rounded bg-gray-950 p-4">
          {!config ? (
            <p className="text-base text-gray-600">No config snapshot found — restart the proxy to record one.</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <span className="text-base font-semibold text-gray-400 uppercase tracking-widest">Proxy Config</span>
                <span className="text-base text-gray-600 font-mono">snapshot {new Date(config.timestamp).toLocaleString()}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-1.5">
                {Object.entries(config.config).map(([key, value]) => (
                  <div key={key} className="flex items-baseline gap-2">
                    <span className="text-base text-gray-500 font-mono w-44 shrink-0">{key}</span>
                    <span className="text-base text-gray-200 font-mono truncate" title={String(value)}>{String(value)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Step type legend */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-2">
          {Object.entries(STEP_STYLE).map(([type, s]) => (
            <button
              key={type}
              onClick={() => setActiveLegend(activeLegend === type ? null : type)}
              className={`px-1.5 py-0.5 rounded text-base font-mono border transition-opacity ${s.badge} ${activeLegend && activeLegend !== type ? 'opacity-40' : 'opacity-100'}`}
            >
              {type}
            </button>
          ))}
        </div>
        {activeLegend && (
          <div className={`mt-2 px-3 py-2 rounded border text-base ${STEP_STYLE[activeLegend].badge}`}>
            <span className="font-semibold font-mono mr-2">{activeLegend}</span>
            <span className="opacity-80">{STEP_DESC[activeLegend]}</span>
          </div>
        )}
      </div>

      {/* Task list */}
      {tasks.length === 0 ? (
        <div className="text-center text-gray-600 py-12">No tasks logged yet.</div>
      ) : (
        tasks.map(task => (
          <TaskCard key={task.task_id} task={task} onDeleted={() => fetchTasks(page)} />
        ))
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 text-base text-gray-500">
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
            <p className="text-base text-gray-400 mb-6">
              This will permanently delete all {total} tasks and every step within them. This cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteAllModal(false)}
                className="px-4 py-2 rounded text-base bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAll}
                className="px-4 py-2 rounded text-base bg-red-700 text-white hover:bg-red-600 transition-colors font-semibold"
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
