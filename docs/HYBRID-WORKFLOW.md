# Hybrid Workflow — Gemini + Claude Code + Cline + Local LLM

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
| Develop algorithms | Gemini | Develop the plan / algorithms, refined over a number of conversation iterations |
| Understand the codebase | Claude Code | Full context window, strong reasoning, reads multiple files |
| Plan the approach | Claude Code | Architectural thinking using the Gemini 'plan' also knows what already exists |
| Write the Cline prompt | Claude Code | Knows exactly what to ask for and how to phrase it |
| Execute the code change | Cline + local LLM | Fast, local, no API cost, reliable when given a precise task |

Claude Code does the thinking. Cline does the doing.

---

## Quick Reference

| Task | Use |
|---|---|
| Researching algorithms and approaches | Gemini |
| Creating the requirements | Gemini |
| Iterating on a design before touching code | Gemini |
| Uploading a research paper or spec PDF for analysis | Gemini |
| Exploring trade-offs between multiple algorithmic approaches | Gemini |
| Deep Research on a topic (weather models, statistics, etc.) | Gemini |
| Understanding existing code | Claude Code |
| Planning a new feature | Claude Code |
| Writing a Cline prompt | Claude Code |
| Reviewing a Cline output | Claude Code |
| Deciding between approaches | Claude Code |
| Translating a Gemini algorithm plan into codebase-aware steps | Claude Code |
| Executing a specific, well-defined code change | Cline |
| Adding a function to an existing file | Cline |
| Creating a new component from a spec | Cline |
| Repetitive edits across multiple files | Cline |

---

## Gemini Free Tier — What It Offers

Gemini fills the slot in this workflow that neither Claude Code nor a local LLM is best suited for: **open-ended algorithm research and requirements refinement** before any code is written.

### Why free tier is enough

Google AI Studio ([aistudio.google.com](https://aistudio.google.com)) gives free access to Gemini without a subscription. The free tier includes:

- **Gemini 2.5 Pro** — Google's most capable model, available in AI Studio at no cost within daily limits
- **1 million token context window** — paste entire papers, long specifications, or extended conversation histories without truncation
- **Deep Research mode** — Gemini can perform multi-step web research on a topic and return a structured report; useful for surveying weather model approaches, statistical methods, or scoring algorithms before committing to an implementation
- **Multimodal input** — upload PDF papers, diagrams, screenshots of equations, or images of architecture diagrams and Gemini can reason about them directly
- **Code execution** — Gemini can run Python snippets in a sandbox to validate an algorithm idea before you write any project code
- **No rate-limit pressure for long conversations** — free tier limits are generous enough for iterative design sessions that span many back-and-forth exchanges

### What Gemini is good for in this workflow

- **Algorithm design sessions** — have a long, iterative conversation about *how* to approach a problem (e.g. how to score forecast confidence, how to combine multiple model outputs) without worrying about codebase specifics; Gemini will not hallucinate about your files because you have not shown it any
- **Translating research into a spec** — paste a relevant paper or concept and ask Gemini to extract a concrete algorithm description you can hand to Claude Code to implement
- **Requirements refinement** — iterate on what the feature should actually do, edge cases, data sources, and output format, before Claude Code ever reads a file
- **Cross-checking approaches** — describe two candidate designs and ask Gemini which is more statistically sound or easier to maintain; use its answer as the brief you hand to Claude Code

### Gemini → Claude Code handoff

The output of a Gemini session is a **written brief**: an algorithm description, a data flow, a set of requirements, or a numbered design. You paste this brief into Claude Code alongside the codebase-specific question: *"Here is the approach I've settled on. Read these files and tell me how to implement it."* Claude Code bridges the abstract Gemini output and the concrete codebase reality.

---

## How It Works in Practice

### The basic flow

**1. Use Gemini to design the approach**

Before opening Claude Code, use Gemini in [AI Studio](https://aistudio.google.com) to settle on what you actually want to build and how. This is a free-form research and design conversation — no codebase involved yet:

```
I want to add a wind chill calculation to a weather app.
What formula should I use? The app already has temperature in °C
and wind speed in km/h. What are the edge cases I need to handle?
```

Gemini can pull in research, compare formulas, and help you arrive at a concrete spec. The output of this step is a clear description of the algorithm and its requirements — not code, just intent. You can also use Gemini's **Deep Research** mode here to survey how wind chill is defined across different meteorological standards, or upload a reference PDF directly.

When you have a settled approach, copy the key decisions out as a short brief to carry into Claude Code.

**2. Ask Claude Code to understand the codebase**

Open Claude Code and give it context about what you want to build — including the brief from Gemini:

```
I want to add a wind chill calculation to this weather app.
The formula to use is the Environment Canada standard (windChill = 13.12 + 0.6215T - 11.37V^0.16 + 0.3965T*V^0.16).
Look at src/lib/weather-utils.ts and src/types/types.ts and tell me
what already exists and where a windChill function should go.
```

Claude Code will read the files, understand the existing structure, and give you an accurate picture of the codebase — including what functions already exist, what types are in use, and where new code should be placed.

**4. Ask Claude Code to produce a Cline prompt**

Once Claude understands the codebase, ask it to write the execution prompt:

```
Write me a Cline prompt to add a windChill(tempC, windSpeedKph) function
to weather-utils.ts. The prompt should be precise enough for a local LLM
to execute without making mistakes.
```

Claude will produce a prompt that names the exact file, describes the exact function signature, and uses clinerules-compatible phrasing. The local model does not need to figure any of that out — it just executes.

**5. Paste the prompt into Cline**

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

### Gemini's strengths

- 1M token context window — absorbs entire papers, long specs, or dense conversation histories
- Deep Research mode — conducts multi-step web research and synthesises a structured report
- Multimodal — reads PDFs, diagrams, and images directly, useful for algorithm papers
- Code execution sandbox — can validate an algorithm idea in Python before any project code is written
- No subscription cost — AI Studio free tier is sufficient for design and research sessions
- No codebase pressure — because Gemini has not read your files, algorithm conversations stay unconstrained by implementation details

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

**1. Ask Gemini to design the heatmap:**

```
I want to add a temperature heatmap to a weather app. It will show 24 hourly
cells coloured from cold to warm. How should I handle the colour interpolation —
should I use a fixed scale (e.g. -10°C to 35°C) or a relative scale based on
the day's min/max? What are the trade-offs?
```

**Gemini responds:** recommends a relative min/max scale so the heatmap is always visually informative regardless of season, and suggests clamping to avoid edge cases when all 24 hours are the same temperature. This becomes the spec.

**2. Ask Claude Code:**
```
Look at src/app/main-content.tsx, src/components/WeatherTable.tsx,
and src/types/types.ts. I want to add a temperature heatmap —
a 24-cell grid showing each hour coloured from blue (cold) to red (warm),
using a relative scale based on the day's min/max temperature.
What needs to change and what new files are needed?
```

**Claude responds:** explains that a new `TemperatureHeatmap.tsx` component is needed, that `main-content.tsx` needs a new view type and button, and that `temperature2m` is already available in the `HourlyWeatherPoint` type.

**3. Ask Claude to write the Cline prompt:**
```
Write a Cline prompt to create src/components/TemperatureHeatmap.tsx.
It should accept HourlyWeatherPoint[] as props, render a flex-wrap grid
of 24 cells, and interpolate colour from blue (#3b82f6) to red (#ef4444)
based on the min/max temperature range. Include "use client" at the top.
```

**4. Paste into Cline.** Cline creates the file cleanly in one pass.

**5. Ask Claude for the follow-up prompt:**
```
Now write a Cline prompt to update main-content.tsx to add the heatmap view —
add "heatmap" to ViewType, add a button, import TemperatureHeatmap, and
add a render block. Use read_repo_file first.
```

**6. Paste into Cline.** Done.

Notice that Gemini never touched the codebase — it settled the design question before any files were opened. Claude never wrote a line of application code — it planned, directed, and translated intent into precise instructions. Cline never made a decision — it executed exactly what it was told.

---

## Patterns That Work Well

**Use Gemini to settle design questions before opening the codebase.** Any question of the form "what is the best way to…" or "should I use X or Y" belongs in Gemini first. Typical prompts:

- *"I want to score forecast confidence across multiple weather variables. What statistical approaches are commonly used for this? What are the trade-offs between a weighted average and a percentile-based method?"*
- *"My weather app shows 24-hour temperature data. What colour scale would be most intuitive for a heatmap — perceptually uniform like viridis, or blue-to-red? What are the accessibility considerations?"*
- *"I need to combine Open-Meteo and a secondary weather source. What are common strategies for reconciling disagreeing forecasts? Should I average, take the most recent, or weight by historical accuracy?"*
- *"What is the standard formula for apparent temperature (feels-like) that accounts for both wind chill and heat index? What are the temperature and wind speed thresholds where each applies?"*

Carry the answer forward as a one-paragraph brief when you switch to Claude Code.

**Use Gemini's Deep Research mode for domain background.** When you need to understand a meteorological concept, a statistical method, or an API's data model before writing any code, ask Gemini to research it:

- *"Research how Open-Meteo encodes weather codes and what the full WMO code table looks like. Summarise which ranges map to which weather categories."*
- *"Research common approaches to detecting anomalous weather data in time-series sensor readings. Summarise the methods most suitable for a real-time app with no historical baseline."*

Deep Research returns a structured report with sources. You do not need to trust it blindly — but it gives you a grounded starting point to hand to Claude Code rather than asking Claude to reason from scratch about an unfamiliar domain.

**Ask Claude to break large tasks into a sequence.** For anything touching more than one file, ask explicitly: *"Break this into a sequence of Cline prompts, one task each, in the right order."* Claude will produce a numbered list you can work through one at a time.

**Name the file in every Cline prompt.** The proxy skips enrichment when a file path is present and Cline reads the file directly instead — this gives the local model clean, accurate content rather than retrieved chunks. Always include `src/path/to/file.ts` in prompts that involve an edit.

**Ask Claude to check before suggesting.** Before asking for a prompt, verify: *"Does a wind chill function already exist in weather-utils.ts?"* This costs one Claude message and prevents Cline from adding a duplicate.

**Let Claude write the clinerules-safe phrasing.** Claude knows the clinerules in this project. When it writes a Cline prompt it will naturally use "edit", "add", or "update" rather than vague language that might trigger unwanted behaviour from the local LLM.

**Keep Cline tasks small.** One function, one component, one targeted edit per task. Larger tasks increase the chance of a SEARCH/REPLACE failure or an unwanted side effect. Claude is good at scoping — ask it to keep the prompt focused.

**Use Claude for review after anything non-trivial.** After Cline creates a new component or makes a multi-line edit, paste the result back to Claude: *"Cline produced this — does it look correct?"* The local model occasionally misses a missing import or a type mismatch that Claude will catch immediately.
