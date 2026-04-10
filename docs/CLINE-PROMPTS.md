# Cline Prompt Examples

> **Note:** These prompts are written for the setup described in [AI-SETUP.md](AI-SETUP.md) — with the proxy running and the `context-engine` MCP server active. Replace `stoodleyweather` with the name of your own repo.

## How context works in this setup

The proxy automatically injects relevant code chunks from ChromaDB into every Cline request. You do not need to explicitly call `semantic_search` for most tasks — the proxy handles it in the background.

When a prompt contains a file path (e.g. `src/lib/weather-utils.ts`), the proxy skips enrichment and Cline reads the file directly via `read_repo_file` instead. This gives the model clean, accurate file content for edits.

**Rule of thumb:**
- For edits to a specific file — include the file path in your prompt
- For exploratory questions about the codebase — omit the file path and let the proxy inject context

---

## Reading & Understanding Code

```
Read the file src/api/weather.ts and explain what it does
```
```
Read src/app/main-content.tsx and list all the props each component receives
```
```
Read src/types/types.ts and summarise the data structures used in this project
```
```
Read src/lib/weather-utils.ts and list all the exported functions
```

---

## Adding Functions to Existing Files

These prompts follow the clinerules pattern — always read the file first, append to the end, never rewrite the whole file.

```
Read src/lib/weather-utils.ts in stoodleyweather, then add a function windChill(tempC: number, windSpeedKph: number): number that calculates wind chill using the standard formula
```
```
Read src/lib/weather-utils.ts in stoodleyweather, then add a function celsiusToFahrenheit(celsius: number): number
```
```
Read src/lib/weather-utils.ts in stoodleyweather, then add a function formatTemperature(tempC: number): string that returns the value to one decimal place with a °C suffix
```

---

## Editing Existing Files

```
Read src/api/weather.ts in stoodleyweather and add error handling if the API returns a non-200 response
```
```
Read src/app/header.tsx in stoodleyweather and add a last-updated timestamp below the title
```
```
Read src/app/main-content.tsx in stoodleyweather and fix the indentation on the heatmap render block
```

---

## Creating New Components

```
Create src/components/WindRose.tsx — a simple SVG component that accepts direction: string and speed: number as props and renders a directional arrow. Use "use client" at the top.
```
```
Create src/components/PressureTrend.tsx — accepts data: HourlyWeatherPoint[] and renders a rising/falling/steady indicator based on the first and last pressure values. Import HourlyWeatherPoint from @/types/types.
```

---

## Verification

Run after any code change to check for type errors, lint violations, or build failures. The tool auto-detects the project type — no arguments beyond the repo name needed.

```
Call verify_project for stoodleyweather and report the results
```

*Combined with an edit — verify immediately after the change:*
```
Read src/lib/weather-utils.ts in stoodleyweather, add a windChill(tempC: number, windSpeedKph: number): number function, then call verify_project to confirm there are no type errors
```
```
Read src/components/WeatherTable.tsx in stoodleyweather, fix the missing import for HourlyWeatherPoint, then call verify_project to confirm it passes
```
```
Create src/components/PressureTrend.tsx as described, then call verify_project for stoodleyweather before finishing
```

---

## Debugging

```
Read src/api/weather.ts in stoodleyweather and check if latitude and longitude are being passed correctly to the API
```
```
Read src/lib/weather-db.ts in stoodleyweather and check if errors from IndexedDB are being surfaced to the caller
```
```
Search for all console.log statements in stoodleyweather and remove them
```

---

## Adding Features

```
Read src/types/types.ts and src/api/weather.ts in stoodleyweather, then add support for fetching UV index data from the open-meteo API
```
```
Read src/app/main-content.tsx and src/components/WeatherTable.tsx in stoodleyweather, then add a "Show UV Index" button and table view
```

---

## Next.js Docs

```
Use search_nextjs_docs to find how App Router layouts work
```
```
Use search_nextjs_docs to find how to create an API route in Next.js
```
```
Use search_nextjs_docs to find how server components differ from client components
```
```
Use search_nextjs_docs to find how to fetch data in a server component
```
```
Use search_nextjs_docs to find how dynamic routing works in the App Router
```
```
Use search_nextjs_docs to find how to use middleware in Next.js
```
```
Use search_nextjs_docs to find how to configure next.config.js
```

*Search docs then implement:*
```
Use search_nextjs_docs to find how to create an API route, then read src/app/api/weather/route.ts in stoodleyweather and add error handling that returns a 500 response with a message on failure
```

---

## TypeScript Docs

```
Use search_typescript_docs to find how generic constraints work
```
```
Use search_typescript_docs to find how mapped types are defined
```
```
Use search_typescript_docs to explain conditional types
```
```
Use search_typescript_docs to find all available utility types
```
```
Use search_typescript_docs to find what the strict tsconfig option enables
```
```
Use search_typescript_docs to find the difference between type and interface
```

*Search docs then implement:*
```
Use search_typescript_docs to find how mapped types work, then read src/types/types.ts in stoodleyweather and add a utility type that makes all properties of HourlyWeatherPoint optional
```

---

## React Docs

```
Use search_react_docs to find how to use the useEffect hook
```
```
Use search_react_docs to find how React context works
```
```
Use search_react_docs to find how useRef differs from useState
```
```
Use search_react_docs to find how React 19 server actions work
```

*Search docs then implement:*
```
Use search_react_docs to find how to use the useEffect hook, then read src/app/main-content.tsx in stoodleyweather and add a useEffect that logs when weatherData changes
```

---

## Project-Wide Understanding

```
Read src/app/page.tsx in stoodleyweather and trace through all the components it renders, reading each one
```
```
Read src/types/types.ts in stoodleyweather and give me a summary of all the weather data fields available
```
```
Read src/lib/weather-utils.ts and src/components/SummitConditions.tsx in stoodleyweather and explain how the summit score is calculated and displayed
```
