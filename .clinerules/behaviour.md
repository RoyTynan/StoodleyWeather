# Behaviour Rules

## Response Length — CRITICAL RULE
Keep responses short. The user can see the file being edited in real time — they do not need it explained.

NEVER include any of the following:
- Preamble before doing the task ("I'll now...", "Sure, let me...", "To do this I will...")
- Explanation of what you just did after doing it beyond a single confirmation line
- Reasoning or thinking out loud
- Next steps or suggestions unless explicitly asked
- Follow-up questions unless the task is genuinely ambiguous

After completing a task, respond with ONE short confirmation line only. Example: "Done — added `mpsToBeaufort` to `weather-utils.ts`." Then stop.

For read or search tasks (no file edits), answer the question in one or two sentences then call `attempt_completion` once with the answer as the result. Do NOT call `attempt_completion` more than once.

## Editing Files
- Do NOT edit any file unless the user explicitly uses the word "edit", "change", "fix", or "update".
- A search or lookup result is never a reason to edit a file.
- If you find a problem in a file (duplicate line, error, etc.) while searching, report it to the user — do NOT fix it unless explicitly asked.

## Running Terminal Commands
- Do NOT run any terminal command unless the user explicitly uses the word "run" or "execute".
- Do NOT run the dev server, compiler, or any build tool unless explicitly asked.

## Before Creating Files
- Do not create new files without asking first.
- Confirm the file name, location, and purpose before proceeding.
- If editing an existing file would achieve the same result, prefer that over creating a new file.
- Do not assume a React component is needed. Only create a component if explicitly asked, or if the task clearly requires UI output. Utility functions, API helpers, types, and hooks are all valid outputs on their own.
- If the type of output (component, function, type, etc.) is ambiguous, ask first.


## Before Large Tasks
- If a task will involve changes to more than one file, briefly explain your plan before writing any code.
- Wait for the user to confirm the plan before proceeding.
- If the scope of a task is unclear, ask a clarifying question rather than making assumptions.

## Running the Dev Server or Tests — CRITICAL RULE
- NEVER run `npm test`, `npm run test`, `jest`, or any test command unless the user explicitly says "run the tests".
- NEVER run `npm run dev`, `npm start`, or any dev server command unless explicitly asked.
- NEVER run any terminal command as part of a search or code-reading task.
- The dev server runs on the i7 Ubuntu server — it is not accessible at `localhost` on the user's Mac.

## Editing Existing Files — CRITICAL RULE
**NEVER output the entire contents of an existing file.** This is the most important rule in this document.

When adding a function to an existing file, follow these exact steps:
1. Read the file using `read_repo_file`.
2. Write an edit that contains ONLY the new function — nothing else.
3. Place the new function at the END of the file, after all existing content.
4. The edit must NOT include any existing lines from the file.

When appending a new function, you MUST use the last line of the existing file as your search anchor. Structure the edit like this:

- SEARCH: the last line of the existing file (e.g. `}` or the closing line)
- REPLACE: that same last line, followed by a blank line, followed by the new function

CORRECT edit structure:
```
SEARCH: }
REPLACE: }

export function newFunction(): void {
  // implementation
}
```

This preserves all existing content and places the new function after it.

WRONG — do NOT use an empty search string or output the whole file. Do NOT add a "// new function only" comment. If your edit replaces the entire file content, you have made a critical error.

## Deleting and Renaming — CRITICAL RULE
- NEVER delete, remove, or comment out existing code unless the user explicitly asks you to remove something.
- NEVER rename or move a file without explicit instruction.
- If a task could be interpreted as requiring deletion or renaming, ask first.

## Refactoring
- Do not refactor, tidy, or reorganise code that was not part of the original request.
- If you notice an improvement outside the scope of the task, mention it as a suggestion — do not make the change uninstructed.
- Only touch the files directly relevant to the task at hand.
