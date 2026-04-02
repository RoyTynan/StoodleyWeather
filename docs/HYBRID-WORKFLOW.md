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

## How It Works in Practice

### Step 1 — Ask Claude Code to understand the codebase

Open Claude Code in the terminal and give it context about what you want to build:

```
I want to add a wind chill calculation to this weather app.
Look at src/lib/weather-utils.ts and src/types/types.ts and tell me
what already exists and where a windChill function should go.
```

Claude Code will read the files, understand the existing structure, and give you an accurate picture of the codebase — including what functions already exist, what types are in use, and where new code should be placed.

### Step 2 — Ask Claude Code to produce a Cline prompt

Once Claude understands the codebase, ask it to write the Cline prompt:

```
Write me a Cline prompt to add a windChill(tempC, windSpeedKph) function
to weather-utils.ts. The prompt should be precise enough for a local LLM
to execute without making mistakes.
```

Claude will produce a prompt that:
- Names the exact file to edit
- Describes the exact function signature and behaviour
- Uses the correct clinerules-compatible phrasing ("add", "edit", "update")
- Avoids ambiguity that would cause the local LLM to guess

### Step 3 — Paste the prompt into Cline

Copy the prompt Claude produced and paste it into Cline. Cline will:
1. Read the file via the MCP `read_repo_file` tool
2. Write a targeted edit (not a full file rewrite)
3. Confirm with a single line

The proxy enriches the request with relevant code context from ChromaDB before it reaches the local LLM, so the model has the surrounding codebase as background even for short prompts.

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

The proxy injects relevant code chunks into every Cline request automatically. Even a short prompt like "add windChill to weather-utils.ts" arrives at the local LLM with the current contents of related files already in context. This significantly reduces hallucination on file edits.

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

---

## Tips

**Be specific about file paths in Claude prompts.** Claude reads the actual files — the more specific you are, the more accurate its understanding and the better the Cline prompt it produces.

**Ask Claude to check before suggesting.** If you're unsure whether something already exists, ask Claude to read the file first: *"Look at weather-utils.ts — does a wind chill function already exist?"*

**Let Claude write the clinerules-safe phrasing.** Claude knows the clinerules in this project. When it writes a Cline prompt it will naturally use "edit", "add", or "update" rather than vague language that might trigger unwanted behaviour from the local LLM.

**Keep Cline tasks small.** One function, one component, one edit per Cline task. Claude is good at breaking a larger goal into a sequence of small, precise Cline prompts. Ask it to do this explicitly: *"Break this into a sequence of Cline prompts, one task each."*

**Use Claude for review.** After Cline makes a change, paste the result back to Claude: *"Cline produced this — does it look correct?"* Claude will spot issues that the local LLM missed.

---

## When to use each tool

| Task | Use |
|---|---|
| Understanding existing code | Claude Code |
| Planning a new feature | Claude Code |
| Writing a Cline prompt | Claude Code |
| Reviewing a Cline output | Claude Code |
| Executing a specific, well-defined code change | Cline |
| Adding a function to an existing file | Cline |
| Creating a new component from a spec | Cline |
| Running a search or file read | Either |
