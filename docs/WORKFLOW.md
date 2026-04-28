# Working with Cline

How to get the best results from the proxy setup — when to use RAG context, when to read files directly, how to write effective prompts, and how to combine Cline with Claude Code.

---

## How Context Works

Every Cline prompt passes through the proxy before reaching the LLM. The proxy automatically enriches it:

1. Detects which repo the conversation is about
2. Runs hybrid search (vector + BM25 + rerank) to find the most relevant code chunks
3. Injects a codebase skeleton map and the top-ranked chunks into the prompt
4. Forwards the enriched prompt to the LLM

This means the LLM always receives codebase context — even for short prompts that do not explicitly reference files.

**Enrichment is skipped when:**
- The prompt contains a file path matching `src/...` — Cline reads that file directly via `read_repo_file` instead, giving the model clean accurate file content
- The message starts with `[` — it is a Cline internal tool result, not a user prompt

**Rule of thumb:**
- For edits to a specific file — include the path in the prompt, let Cline read it directly
- For exploratory questions about the codebase — omit the path and let the proxy inject context

---

## Writing Effective Prompts

### Name the file for edits

```
Read src/lib/weather-utils.ts in stoodleyweather, then add a windChill(tempC: number, windSpeedKph: number): number function
```

Including the path triggers direct file read — the model receives the exact current file content, not a retrieved chunk. This is more reliable for edits.

### Omit the path for exploration

```
What functions handle temperature conversion in stoodleyweather?
```

Without a file path, the proxy injects the most relevant chunks from across the codebase. Good for "where is X" and "how does Y work" questions.

### Keep tasks small

One function, one component, one targeted edit per Cline task. Larger tasks increase the chance of a SEARCH/REPLACE failure or an unwanted side edit. If the task touches multiple files, break it into a sequence — one prompt per file.

### Always read before editing

```
Read src/app/main-content.tsx in stoodleyweather, then add a "Heatmap" button to the view selector
```

Reading first gives the model the exact current state of the file. Edits based on retrieved chunks can fail if the chunk is slightly out of date.

### Verify after edits

```
Read src/lib/weather-utils.ts in stoodleyweather, add a windChill function, then call verify_project to confirm there are no type errors
```

`verify_project` runs type-check and lint and returns the output. If there are errors, Cline can fix them immediately within the same task.

---

## Prompt Examples

### Reading and understanding

```
Read src/api/weather.ts and explain what it does
```
```
Read src/types/types.ts and summarise the data structures used in this project
```
```
Read src/lib/weather-utils.ts and list all the exported functions
```

### Adding functions

```
Read src/lib/weather-utils.ts in stoodleyweather, then add a function celsiusToFahrenheit(celsius: number): number
```
```
Read src/lib/weather-utils.ts in stoodleyweather, then add a function formatTemperature(tempC: number): string that returns the value to one decimal place with a °C suffix
```

### Creating new components

```
Create src/components/WindRose.tsx — a simple SVG component that accepts direction: string and speed: number as props and renders a directional arrow. Use "use client" at the top.
```
```
Create src/components/PressureTrend.tsx — accepts data: HourlyWeatherPoint[] and renders a rising/falling/steady indicator based on the first and last pressure values. Import HourlyWeatherPoint from @/types/types.
```

### Editing existing files

```
Read src/app/header.tsx in stoodleyweather and add a last-updated timestamp below the title
```
```
Read src/api/weather.ts in stoodleyweather and add error handling if the API returns a non-200 response
```

### Verification

```
Call verify_project for stoodleyweather and report the results
```
```
Read src/components/WeatherTable.tsx in stoodleyweather, fix the missing import for HourlyWeatherPoint, then call verify_project to confirm it passes
```

### Using framework documentation

```
Use search_nextjs_docs to find how App Router layouts work
```
```
Use search_nextjs_docs to find how to create an API route, then read src/app/api/weather/route.ts in stoodleyweather and add error handling that returns a 500 response on failure
```
```
Use search_typescript_docs to find how mapped types work, then read src/types/types.ts in stoodleyweather and add a utility type that makes all properties of HourlyWeatherPoint optional
```
```
Use search_react_docs to find how to use the useEffect hook, then read src/app/main-content.tsx in stoodleyweather and add a useEffect that logs when weatherData changes
```

### Project-wide understanding

```
Read src/types/types.ts in stoodleyweather and give me a summary of all the weather data fields available
```
```
Read src/lib/weather-utils.ts and src/components/SummitConditions.tsx in stoodleyweather and explain how the summit score is calculated and displayed
```

---

## Clinerules

Each repo has a `.clinerules/` directory that tells Cline how to behave. Rules are split into two files so they can be reused across projects:

- **`.clinerules.md`** — generic rules for any project. Covers assumption surfacing (state interpretation before coding), minimal footprint (no speculative abstractions or extra dependencies), surgical changes (only touch code related to the request), and git behaviour.
- **`.clinerules-typescript.md`** — TypeScript and React-specific rules. Add alongside the generic file for TS projects.

Cline reads all files in `.clinerules/` and stacks them. For a new project, copy both relevant files from this repo.

---

## The Hybrid Workflow — Cline + Claude Code

For direct, targeted tasks — add this function, edit this component, fix this type — Cline with the proxy handling context is fast and reliable. For tasks that require reasoning across the whole codebase or planning a multi-file feature, combine Cline with Claude Code.

| Role | Tool |
|---|---|
| Understand existing code | Claude Code |
| Plan a multi-file feature | Claude Code |
| Write a precise Cline prompt | Claude Code |
| Review a Cline output | Claude Code |
| Execute a targeted file edit | Cline |
| Add a function to an existing file | Cline |
| Create a new component from a spec | Cline |
| Repetitive edits across files | Cline |

### The basic flow

**1. Ask Claude Code to understand the codebase**

```
Look at src/lib/weather-utils.ts and src/types/types.ts and tell me
what already exists and where a windChill function should go.
```

Claude reads the files, understands the existing structure, and tells you what already exists — preventing Cline from duplicating things.

**2. Ask Claude Code to write the Cline prompt**

```
Write a Cline prompt to add a windChill(tempC, windSpeedKph) function
to weather-utils.ts. Make it precise enough for a local LLM to execute
without making mistakes.
```

Claude produces a prompt that names the exact file, uses the correct function signature, and follows clinerules conventions.

**3. Paste the prompt into Cline**

Cline reads the file, makes the targeted edit, and confirms. The proxy enriches the request automatically.

### When to stay in Claude

- You are not sure what the codebase already has — read the files before writing any prompt
- The task touches more than one file — Claude plans the sequence, Cline executes each step
- Something Cline produced looks wrong — bring it back to Claude for review before asking Cline to retry
- You are deciding between two approaches — Claude reasons about trade-offs; the local model will just pick one

### When to switch to Cline

- You have a precise, single-file task with a clear description
- The task is repetitive
- Claude has already read the relevant files and produced the prompt

### Working back and forth

Real sessions are iterative. A typical mid-feature loop:

1. **Claude** reads three files, plans the change, produces a Cline prompt
2. **Cline** executes — creates a new component
3. Something doesn't look right — bring it back to **Claude**: *"Cline produced this. The colour classes don't match WeatherTable — look at WeatherTable and write a correction prompt."*
4. **Claude** reads WeatherTable, spots the pattern, writes the correction
5. **Cline** applies it

Claude handles every step that requires reading or reasoning. Cline handles every step that requires writing to a file.

---

## Adding Gemini for Algorithm Design

For open-ended research and algorithm design before any code is written, Gemini at [aistudio.google.com](https://aistudio.google.com) is useful. The free tier includes Gemini 2.5 Pro with a 1M token context window, Deep Research mode, and the ability to read PDFs and diagrams.

Use Gemini for:
- Settling on an algorithm before opening the codebase (*"Should I use a fixed or relative scale for the temperature heatmap? What are the trade-offs?"*)
- Surveying a domain before writing code (*"Research how Open-Meteo encodes weather codes and summarise the WMO code ranges"*)
- Iterating on requirements and edge cases

The output of a Gemini session is a written brief — an algorithm description or a set of requirements. Paste that brief into Claude Code alongside a codebase question. Claude bridges the abstract Gemini output and the concrete codebase.

Gemini never needs to see your source files. Claude never needs to research the domain from scratch. Cline never needs to make a design decision.

---

## Dependency Impact Notes

After every file write, the proxy automatically checks which other files import the file that was just edited. If any are found, the LLM's next prompt includes an impact note like this:

```
Dependency impact: `src/lib/weather-utils.ts` is also imported by:
  - src/components/WeatherTable.tsx
  - src/components/SummitConditions.tsx
```

This tells the LLM where to look for knock-on effects — broken imports, type mismatches, callers that may no longer match the updated signature — without you having to ask. The LLM can then choose to read those files and check them, or flag them in its completion message.

**You do not need to do anything.** The impact note is injected automatically. If the LLM spots a problem in a dependent file it will usually address it in the same task. If it does not, use the impact note as a prompt:

```
The impact note said SummitConditions.tsx also imports weather-utils.ts.
Read it and check the windChill call still matches the updated signature.
```

The impact check is powered by a dependency graph built at index time — `index_repos.py` parses all `import` and `require` statements and stores edges in `dep_graph.db`. It is rebuilt on every index run and kept current by the file watcher. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical details.

---

## Why Prompts Succeed or Fail

**"Read and understand the entire project"** — a common failure. The model starts reading files one by one via `read_file`, fills the context window, and hits a HALT. The proxy cannot help because the prompt contains file paths.

**"Read every file listed in the codebase structure above"** — works, because the model uses `read_repo_file` from the context-engine MCP server (which is aware of what files exist) rather than repeatedly calling `read_file`. The proxy's skeleton injection is used to guide the model to a structured approach.

The distinction: prompts that ask the model to *use the injected context and MCP tools* work far better than prompts that ask the model to *read everything from scratch*. The proxy has already done the retrieval work — well-written prompts let the model use it.
