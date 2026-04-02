# Environment Variable Rules

## General
- Never hardcode values that belong in environment variables (API keys, tokens, URLs, secrets).
- Never expose environment variables in client-side code unless they are prefixed with `NEXT_PUBLIC_` and are intentionally public.
- Do not log environment variable values to the console.

## Files
- Environment variables belong in `.env.local` — never commit this file.
- Do not modify `.env.local`, `.env`, or any other env file without being explicitly asked.
- If a new environment variable is needed, tell the user what to add and where — do not write it to the file yourself.

## Next.js Specifics
- Server-only secrets must never be prefixed with `NEXT_PUBLIC_`.
- Only prefix a variable with `NEXT_PUBLIC_` if it genuinely needs to be accessible in the browser.
