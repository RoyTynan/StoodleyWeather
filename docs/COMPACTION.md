# Context Compaction

How the system manages conversation context growth across a long Cline task.

---

## The Problem

Every step in a Cline task — file reads, tool results, code writes, verify outputs, LLM responses — is appended to the message array and resent to the LLM on the next request. The array grows continuously. Left unchecked it reaches the model's context window limit, producing an empty response and a HALT.

Two forces drive the growth:

- **Bulk content** — fenced code blocks in LLM responses, full file contents from read results, large tool output bodies. These are large but low-value once the LLM has processed them.
- **Prose and summaries** — plain-text reasoning, injected skeleton maps, enriched context chunks. These are smaller but semantically dense and cannot be stripped blindly.

---

## Why the LLM Cannot Compact Its Own Context

The obvious approach — ask the LLM to summarise the full conversation when it gets long — fails in practice. By the time the conversation is large enough to need compacting, it is already too large to fit in the context window alongside the summarisation instruction. The compaction request swamps the resource it is trying to free, producing empty responses and HALT rather than a useful summary.

---

## Two-Layer Compaction

The system uses two complementary techniques running in parallel. Together they cover what neither can handle alone.

### Layer 1 — Regex Sliding Window Pruning

Runs on **every request**, automatically, with no LLM call.

The proxy strips bulk content from messages older than `PRUNE_KEEP_LAST_N` (default: 4) before forwarding to the LLM:

- **Fenced code blocks** (`` ``` ... ``` ``) → replaced with `[Code block omitted]`
- **Tool result bodies** — content following a `[use_mcp_tool ...]` or `[read_file ...]` header → replaced with `[Content omitted]`, header kept for conversation coherence

The last `PRUNE_KEEP_LAST_N` messages are always kept intact. Savings per request are recorded in the `chars_pruned` column of `prompt_log.db` and visible in the monitor.

**What this handles well:** large code blocks in LLM responses, full file contents from read results, verbose tool output bodies.

**What this cannot handle:** plain prose, injected skeleton maps, enriched code chunk preambles — none of these use fenced code block syntax so regex leaves them untouched.

### Layer 2 — Lite LLM Per-Step Compaction

Runs in the **background** as a one-off thread, triggered when `prompt_tokens` on a completed step crosses `COMPACT_TRIGGER_TOKENS` (default: 20000).

Rather than summarising the whole conversation (which causes saturation), it summarises **individual old messages one at a time**:

1. After an LLM response is received and logged, a background thread checks whether `prompt_tokens` has crossed the trigger threshold
2. If yes, it walks the old messages (older than `PRUNE_KEEP_LAST_N`) looking for messages above `COMPACT_MIN_CHARS` that do not yet have a stored summary
3. For each qualifying message it sends just that message to the **local Ollama LLM** (Qwen2.5:3b on the i7, port 11434) with a short compression instruction: *"Summarise this in 2–3 sentences, preserving any file names, function names, and error messages."* Using the local model keeps compaction independent of the i9 and frees the heavier model for actual coding tasks.
4. The summary is written to a new `summary` column in the `prompts` table, linked by message position and task ID
5. On the next proxy request, messages that have a stored summary have their content replaced with the summary before the array is forwarded to the LLM

Each individual message is small (hundreds to low thousands of tokens), so the summarisation call never risks saturation. The main LLM call and the summary call are independent — Cline never waits for the background compaction.

**What this handles well:** plain prose, reasoning text, injected context preambles — content that regex cannot strip but the LLM can compress meaningfully.

**What this cannot handle:** very short messages (not worth a round trip), messages that are already summaries of summaries (quality degrades).

---

## Configuration Constants

All tuning values live in `config.py` under the `CONTEXT COMPACTION` section:

| Constant | Default | Description |
|---|---|---|
| `PRUNE_KEEP_LAST_N` | `4` | Messages kept fully intact by regex pruning. Higher = more context preserved, slower pruning. |
| `COMPACT_ENABLED` | `True` | Master switch for Layer 2 LLM compaction. Layer 1 regex pruning always runs regardless. |
| `COMPACT_TRIGGER_TOKENS` | `20000` | Prompt token count that triggers a background LLM compaction pass. |
| `COMPACT_MIN_CHARS` | `500` | Minimum message length to be worth summarising. Short messages are left verbatim. |
| `COMPACT_LLM_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint for the local compaction LLM (Ollama on the i7). |
| `COMPACT_LLM_MODEL` | `qwen2.5:3b` | Model name passed to the compaction LLM. |

---

## compact_context MCP Tool

The `compact_context` tool in `server.py` can be called on demand to report the current compaction state:

- How much regex pruning is saving per request (`chars_pruned` from the latest step)
- How many messages in the current task have been LLM-summarised (Layer 2)
- Current prompt token count

The tool logs itself to `prompt_log.db` with `step_type=COMPACT` so the call is visible in the monitor. This is necessary because MCP tools are called directly by the client — the proxy never sees the request and cannot log it automatically.

---

## HALT Recovery

When `COMPACT_ENABLED = True`, a HALT (empty LLM response or `finish_reason=length`) triggers a synchronous compaction pass before giving up:

1. The proxy calls `_summarise_old_messages` synchronously (not as a background thread)
2. If at least one new summary was produced, the proxy rebuilds the context with summaries swapped in and retries the LLM request once
3. If the retry succeeds, the HALT is never shown to the user — the task continues transparently
4. If no new summaries could be produced (all messages already summarised, or LLM unreachable), the normal HALT response is returned

This means `COMPACT_ENABLED = True` changes HALT from a hard stop into a recovery mechanism. The HALT step type is only written to the log if recovery fails.

---

## Interaction Between Layers

The two layers are additive. On any given request:

1. Regex pruning runs first — strips code blocks and tool result bodies from old messages
2. If LLM summaries exist for any old messages, those are swapped in after regex pruning

A message that has been LLM-summarised will not be regex-pruned again (the summary is plain prose, not a code block). A message that has already been regex-pruned will produce a smaller input to the LLM summariser when Layer 2 eventually processes it — so Layer 1 actively reduces the cost of Layer 2.

---

## What Is Never Pruned

The proxy-injected code chunks (skeleton map + relevant source from ChromaDB) are injected into the **most recent** user message, which is always within the `PRUNE_KEEP_LAST_N` window and therefore never touched by either layer. The RAG context is always fully available to the LLM on the current step.

---

## Monitor Display

When Layer 2 background compaction completes for a task, the proxy writes an `AUTOCOMP` step to `prompt_log.db`. This step appears in the task timeline in the monitor (violet badge) alongside TASK, READ, WRITE, and other steps — showing how many messages were summarised in that pass.

The `COMPACT` step (cyan) is written when the `compact_context` MCP tool is called manually. The `AUTOCOMP` step (violet) is written automatically by the background compaction thread.

---

## Implementation Status

| Feature | Status |
|---|---|
| Layer 1 — regex sliding window pruning | Implemented |
| `chars_pruned` column in `prompt_log.db` | Implemented |
| `compact_context` MCP tool (reporting) | Implemented |
| Config constants (`PRUNE_KEEP_LAST_N` etc.) | Implemented |
| Layer 2 — background LLM per-step compaction | Implemented |
| `message_summaries` table in `prompt_log.db` | Implemented |
| HALT recovery — compact and retry on empty response | Implemented |
| `AUTOCOMP` step type in monitor | Implemented |
