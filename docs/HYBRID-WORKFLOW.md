# Hybrid Workflow — Claude Code + Cline + Local LLM

This document describes how to combine Claude Code (Anthropic's cloud-based reasoning model) with Cline and a locally-hosted LLM to get the best of both worlds: strong reasoning and codebase understanding from Claude, with fast local execution from Cline.

---

## Cost

Using Claude Code this way — for reasoning, planning, and writing prompts rather than executing every line of code — keeps token usage low enough to stay comfortably within the **Claude Pro subscription at £17/month ($20/month)**. You are not paying per token or per API call.

The heavy, repetitive work (file reads, code generation, edits) is handled entirely by your local LLM at zero ongoing cost. Claude is used only for the high-value thinking that the local model genuinely struggles with — understanding the codebase, planning changes, and producing precise prompts.

This is a significant advantage over using Claude Code (or any cloud model) as the primary coding assistant, where token costs from large context windows and repeated file reads can quickly exceed a flat monthly subscription.

---

## Local LLMs — What They Can and Cannot Do

A 32B parameter local model is capable of writing good code when given a precise, well-scoped instruction. The proxy setup in this project goes a long way towards making that possible automatically — injecting relevant code context from ChromaDB into every request so the model always has the surrounding codebase in view.

Where a local model still benefits from guidance:

- Reasoning about a large codebase as a whole — understanding how pieces fit together
- Planning a multi-file feature from scratch
- Producing a precise, well-scoped prompt for itself
- Architectural decisions and trade-offs

For direct, targeted tasks — add this function, edit this component, fix this type — the local LLM with the proxy handling context is fast and reliable. The hybrid workflow is about using Claude for the parts where strong reasoning genuinely adds value, not as a crutch for every task.

---

## The Solution — Split the Roles

| Role | Tool | Strengths used |
|---|---|---|
| Understand the codebase | Claude Code | Full context window, strong reasoning, reads multiple files |
| Plan the approach | Claude Code | Architectural thinking, knows what already exists |
| Write the Cline prompt | Claude Code | Knows exactly what to ask for and how to phrase it |
| Execute the code change | Cline + local LLM | Fast, local, no API cost, reliable when given a precise task |

Claude Code does the thinking. Cline does the doing.

---

## Quick Reference

| Task | Use |
|---|---|
| Understanding existing code | Claude Code |
| Planning a new feature | Claude Code |
| Writing a Cline prompt | Claude Code |
| Reviewing a Cline output | Claude Code |
| Deciding between approaches | Claude Code |
| Executing a specific, well-defined code change | Cline |
| Adding a function to an existing file | Cline |
| Creating a new component from a spec | Cline |
| Repetitive edits across multiple files | Cline |

---

## How It Works in Practice

### The basic flow

**1. Ask Claude Code to understand the codebase**

Open Claude Code and give it context about what you want to build:

```
I want to add a wind chill calculation to this weather app.
Look at src/lib/weather-utils.ts and src/types/types.ts and tell me
what already exists and where a windChill function should go.
```

Claude Code will read the files, understand the existing structure, and give you an accurate picture of the codebase — including what functions already exist, what types are in use, and where new code should be placed.

**2. Ask Claude Code to produce a Cline prompt**

Once Claude understands the codebase, ask it to write the execution prompt:

```
Write me a Cline prompt to add a windChill(tempC, windSpeedKph) function
to weather-utils.ts. The prompt should be precise enough for a local LLM
to execute without making mistakes.
```

Claude will produce a prompt that names the exact file, describes the exact function signature, and uses clinerules-compatible phrasing. The local model does not need to figure any of that out — it just executes.

**3. Paste the prompt into Cline**

Cline reads the file via the MCP server, writes a targeted edit, and confirms. The proxy enriches the request with relevant code from ChromaDB before it reaches the local LLM, so even a short prompt arrives with the surrounding codebase already in context.

---

## Recognising the Switch Point

The workflow is not always a clean linear hand-off. In practice you move back and forth between the two tools throughout a session. The question to ask is:

> *Does this step require understanding, or execution?*

**Stay in Claude when:**
- You are not sure what the codebase already has — read the files and find out before writing any prompt
- The task touches more than one file — Claude plans the sequence, Cline executes each step
- Something Cline produced looks wrong — bring it back to Claude for review before asking Cline to retry
- You are deciding between two approaches — Claude can reason about trade-offs; the local model will just pick one

**Switch to Cline when:**
- You have a precise, single-file task with a clear description
- The task is repetitive — adding similar functions, updating multiple imports, renaming across a file
- Claude has already read the relevant files and produced the prompt — just hand it over

A common mistake is staying in Claude too long and asking it to generate code directly rather than write a Cline prompt. Claude can do this, but it means you then have to manually copy the code into the right file. Let Cline handle the file I/O — that is what it is there for.

---

## What Goes Wrong Without This Split

**Using the local LLM for planning:**
Ask a local 32B model to plan a multi-file feature from scratch — without reading the files — and it will hallucinate. It will invent function names that do not exist, reference files in the wrong locations, and produce a plan that conflicts with the actual codebase. The proxy injects context for targeted prompts, but it cannot substitute for reading and reasoning across multiple files at once.

**Using Claude for repetitive execution:**
Claude can write code, but it does not make file edits directly in the way Cline does. If you ask Claude to "add this function to weather-utils.ts", it will show you the code in the chat. You then have to copy it, open the file, find the right place, paste it, and save. For a single change this is fine. For five changes across three files it becomes tedious and error-prone. That is Cline's job.

**Asking Cline to figure out the design:**
Cline passes your prompt to the local LLM, which will try to answer it. If the prompt is vague — "add a feature to show wind chill" — the model will make assumptions about file structure, function naming, prop types, and UI placement. Some of those assumptions will be wrong. Claude reads the actual files and removes the ambiguity before Cline ever sees the task.

---

## Working Back and Forth

Real sessions are iterative. A typical mid-feature exchange looks like this:

1. **Claude** reads three files, plans the change, produces a Cline prompt
2. **Cline** executes — creates a new component
3. You notice the component does not quite match the existing style — bring it back to **Claude**: *"Cline produced this. The colour classes don't match how WeatherTable does it — look at WeatherTable and write a correction prompt."*
4. **Claude** reads WeatherTable, spots the pattern, writes a correction prompt
5. **Cline** applies the correction

This loop — plan, execute, review, correct — is the normal rhythm. Claude handles every step that requires reading or reasoning. Cline handles every step that requires writing to a file.

Reviewing Cline's output in Claude is one of the most useful habits to develop. The local model occasionally misses something — a missing import, a type mismatch, a prop that was not wired through. Claude will catch it immediately if you paste the relevant file back and ask: *"Does this look right?"*

---

## Why This Works

### Claude Code's strengths

- Large context window — can read and reason across the entire codebase at once
- Strong reasoning — understands architecture, dependencies, and trade-offs
- Accurate file reads — no hallucination about what already exists
- Prompt engineering — knows how to phrase instructions for a smaller model

### Local LLM's strengths

- Fast execution of well-defined tasks
- No API cost or rate limits
- Private — code never leaves your network
- Reliable when given a precise, unambiguous instruction

### The proxy's role

The proxy injects relevant code chunks into every Cline request automatically — using a hybrid of vector search and BM25 keyword matching, combined via Reciprocal Rank Fusion. Even a short prompt like "add windChill to weather-utils.ts" arrives at the local LLM with the current contents of related files already in context. This significantly reduces hallucination on file edits.

---

## Example — Full Workflow

**Goal:** Add a temperature heatmap component to the weather app.

**1. Ask Claude Code:**
```
Look at src/app/main-content.tsx, src/components/WeatherTable.tsx,
and src/types/types.ts. I want to add a temperature heatmap —
a 24-cell grid showing each hour coloured from blue (cold) to red (warm).
What needs to change and what new files are needed?
```

**Claude responds:** explains that a new `TemperatureHeatmap.tsx` component is needed, that `main-content.tsx` needs a new view type and button, and that `temperature2m` is already available in the `HourlyWeatherPoint` type.

**2. Ask Claude to write the Cline prompt:**
```
Write a Cline prompt to create src/components/TemperatureHeatmap.tsx.
It should accept HourlyWeatherPoint[] as props, render a flex-wrap grid
of 24 cells, and interpolate colour from blue (#3b82f6) to red (#ef4444)
based on the min/max temperature range. Include "use client" at the top.
```

**3. Paste into Cline.** Cline creates the file cleanly in one pass.

**4. Ask Claude for the follow-up prompt:**
```
Now write a Cline prompt to update main-content.tsx to add the heatmap view —
add "heatmap" to ViewType, add a button, import TemperatureHeatmap, and
add a render block. Use read_repo_file first.
```

**5. Paste into Cline.** Done.

Notice that Claude never wrote a line of application code — it planned, directed, and translated intent into precise instructions. Cline never made a decision — it executed exactly what it was told.

---

## Patterns That Work Well

**Ask Claude to break large tasks into a sequence.** For anything touching more than one file, ask explicitly: *"Break this into a sequence of Cline prompts, one task each, in the right order."* Claude will produce a numbered list you can work through one at a time.

**Name the file in every Cline prompt.** The proxy skips enrichment when a file path is present and Cline reads the file directly instead — this gives the local model clean, accurate content rather than retrieved chunks. Always include `src/path/to/file.ts` in prompts that involve an edit.

**Ask Claude to check before suggesting.** Before asking for a prompt, verify: *"Does a wind chill function already exist in weather-utils.ts?"* This costs one Claude message and prevents Cline from adding a duplicate.

**Let Claude write the clinerules-safe phrasing.** Claude knows the clinerules in this project. When it writes a Cline prompt it will naturally use "edit", "add", or "update" rather than vague language that might trigger unwanted behaviour from the local LLM.

**Keep Cline tasks small.** One function, one component, one targeted edit per task. Larger tasks increase the chance of a SEARCH/REPLACE failure or an unwanted side effect. Claude is good at scoping — ask it to keep the prompt focused.

**Use Claude for review after anything non-trivial.** After Cline creates a new component or makes a multi-line edit, paste the result back to Claude: *"Cline produced this — does it look correct?"* The local model occasionally misses a missing import or a type mismatch that Claude will catch immediately.
