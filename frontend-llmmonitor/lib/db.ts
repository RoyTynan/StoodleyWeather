import Database from 'better-sqlite3';

const DB_PATH = '/mnt/storage/prompt_log.db';

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH, { readonly: true });
  }
  return _db;
}

export type PromptSummary = {
  id: number;
  timestamp: string;
  repo: string | null;
  raw_query: string | null;
  skeleton_injected: number;
  chunks_injected: number;
  verify_injected: number;
  finish_reason: string | null;
  latency_ms: number | null;
  msg_size: number;
  model: string | null;
  task_id: string | null;
  step_type: string | null;
  user_task: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
};

export type PromptDetail = PromptSummary & {
  enriched_message: string | null;
  full_messages: string | null;
  response_text: string | null;
};

export type TaskStep = {
  id: number;
  timestamp: string;
  repo: string | null;
  raw_query: string | null;
  step_type: string | null;
  user_task: string | null;
  task_id: string | null;
  skeleton_injected: number;
  chunks_injected: number;
  verify_injected: number;
  finish_reason: string | null;
  latency_ms: number | null;
  model: string | null;
  msg_size: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
};

export type TaskGroup = {
  task_id: string;
  user_task: string | null;
  repo: string | null;
  started_at: string;
  step_count: number;
  total_latency_ms: number | null;
  first_id: number;
  last_id: number;
  steps: TaskStep[];
};

const STEP_SELECT = `
  SELECT id, timestamp, repo, raw_query, step_type, user_task, task_id,
         skeleton_injected, chunks_injected, verify_injected, finish_reason,
         latency_ms, model, prompt_tokens, completion_tokens,
         length(full_messages) as msg_size
  FROM prompts
`;

export function listTasks(limit = 10, offset = 0): TaskGroup[] {
  const db = getDb();

  const headers = db.prepare(`
    SELECT task_id,
           MIN(id) as first_id,
           MAX(id) as last_id,
           MIN(timestamp) as started_at,
           MAX(CASE WHEN step_type = 'TASK' THEN user_task END) as user_task,
           MAX(CASE WHEN step_type = 'TASK' THEN repo END) as repo,
           COUNT(*) as step_count,
           SUM(latency_ms) as total_latency_ms
    FROM prompts
    WHERE task_id IS NOT NULL
    GROUP BY task_id
    ORDER BY first_id DESC
    LIMIT ? OFFSET ?
  `).all(limit, offset) as Omit<TaskGroup, 'steps'>[];

  if (headers.length === 0) return [];

  const placeholders = headers.map(() => '?').join(',');
  const taskIds = headers.map(h => h.task_id);

  const allSteps = db.prepare(`
    ${STEP_SELECT}
    WHERE task_id IN (${placeholders})
    ORDER BY id ASC
  `).all(...taskIds) as TaskStep[];

  const stepsByTask = new Map<string, TaskStep[]>();
  for (const step of allSteps) {
    if (!stepsByTask.has(step.task_id!)) stepsByTask.set(step.task_id!, []);
    stepsByTask.get(step.task_id!)!.push(step);
  }

  return headers.map(h => ({ ...h, steps: stepsByTask.get(h.task_id) ?? [] }));
}

export function countTasks(): number {
  const row = getDb()
    .prepare('SELECT COUNT(DISTINCT task_id) as count FROM prompts WHERE task_id IS NOT NULL')
    .get() as { count: number };
  return row.count;
}

export function deleteTask(taskId: string): number {
  const db = new Database(DB_PATH);
  const result = db.prepare('DELETE FROM prompts WHERE task_id = ?').run(taskId);
  db.close();
  return result.changes;
}

export function listPrompts(limit = 100, offset = 0): PromptSummary[] {
  return getDb()
    .prepare(
      `SELECT id, timestamp, repo, raw_query,
              skeleton_injected, chunks_injected, verify_injected, finish_reason,
              latency_ms, model, task_id, step_type, user_task,
              length(full_messages) as msg_size
       FROM prompts
       ORDER BY id DESC
       LIMIT ? OFFSET ?`
    )
    .all(limit, offset) as PromptSummary[];
}

export function getPrompt(id: number): PromptDetail | null {
  return (
    getDb()
      .prepare(`SELECT id, timestamp, repo, raw_query, enriched_message, full_messages,
                       skeleton_injected, chunks_injected, verify_injected, finish_reason,
                       latency_ms, model, response_text, task_id, step_type, user_task,
                       length(full_messages) as msg_size
                FROM prompts WHERE id = ?`)
      .get(id) as PromptDetail | null
  );
}

export function countPrompts(): number {
  const row = getDb()
    .prepare('SELECT COUNT(*) as count FROM prompts')
    .get() as { count: number };
  return row.count;
}

export function deletePrompt(id: number): boolean {
  const db = new Database(DB_PATH);
  const result = db.prepare('DELETE FROM prompts WHERE id = ?').run(id);
  db.close();
  return result.changes > 0;
}

export function deleteAllPrompts(): number {
  const db = new Database(DB_PATH);
  const result = db.prepare('DELETE FROM prompts').run();
  db.close();
  return result.changes;
}

export type ConfigSnapshot = {
  id: number;
  timestamp: string;
  config: Record<string, string | number>;
};

export function getLatestConfig(): ConfigSnapshot | null {
  const row = getDb()
    .prepare('SELECT id, timestamp, config FROM config_snapshots ORDER BY id DESC LIMIT 1')
    .get() as { id: number; timestamp: string; config: string } | null;
  if (!row) return null;
  return { ...row, config: JSON.parse(row.config) };
}
