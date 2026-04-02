# Testing Rules

## Setup

Jest is configured in this project with the following stack:

- **Jest** — test runner (`npm test`)
- **ts-jest** — TypeScript support
- **@testing-library/react** — component testing
- **@testing-library/jest-dom** — DOM matchers
- **jest-environment-jsdom** — browser DOM simulation for component tests

Config: `jest.config.js` at the project root.

## Running Tests

```bash
npm test                                              # run all tests
npm test -- --testPathPattern=weather.test            # single file
npm test -- --testPathPattern=main-content.test       # single file
```

## Existing Tests

| File | What it tests |
|---|---|
| `src/api/weather.test.ts` | `getWeatherData()` — columnar API transformation, hour indexing, HTTP error handling |
| `src/app/main-content.test.tsx` | `MainContent` — empty storage status message, fetch button disabled state |

## When to Write Tests

- Do not write tests unless explicitly asked to do so.
- If a task involves a pure utility function or API helper, suggest adding a test — but do not write it without confirmation.

## Test Environment

- API tests (`src/api/`) use `testEnvironment: node` (default).
- Component tests (`src/app/`) require `/** @jest-environment jsdom */` at the top of the file.

## Mocking

- Mock `global.fetch` for API tests — no real network calls.
- Mock `../lib/weather-db` for component tests — IndexedDB is not available in jsdom.
- Suppress `console.error` with `jest.spyOn` in tests that intentionally exercise error paths, and restore with `jest.restoreAllMocks()` afterwards.
- Wrap `settle()` / promise resolution calls in `act(async () => { ... })` to avoid React `act()` warnings.

## What to Test

- Unit test pure functions and API utilities in `src/api/`.
- Component tests should cover behaviour the user sees — status messages, disabled states — not implementation details.
- Do not test implementation details — test behaviour and outputs.
