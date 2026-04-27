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
};

export type PromptDetail = PromptSummary & {
  enriched_message: string | null;
  full_messages: string | null;
  response_text: string | null;
};

export function listPrompts(limit = 100, offset = 0): PromptSummary[] {
  return getDb()
    .prepare(
      `SELECT id, timestamp, repo, raw_query,
              skeleton_injected, chunks_injected, verify_injected, finish_reason,
              latency_ms, model, length(full_messages) as msg_size
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
                       latency_ms, model, response_text, length(full_messages) as msg_size
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
