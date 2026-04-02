# Approved Packages

## Currently Approved
The following packages are already in use and approved:

### Production
- `next` — framework
- `react`, `react-dom` — UI library
- `openmeteo` — Open-Meteo weather API client
- `swr` — data fetching

### Dev / Tooling
- `typescript` — language
- `tailwindcss`, `@tailwindcss/postcss` — styling
- `eslint`, `eslint-config-next` — linting
- `@types/node`, `@types/react`, `@types/react-dom` — TypeScript types
- `babel-plugin-react-compiler` — React compiler

### Loaded at Runtime (not in package.json)
- `cesium` — 3D geospatial viewer, loaded from CDN

## Rules
- Do not install any package not on this list without asking the user first.
- If you believe a new package is needed, suggest it and explain why — do not install it automatically.
- Do not install multiple packages that solve the same problem (e.g., two date libraries, two icon sets).
- Prefer packages already in use before suggesting a new dependency.
