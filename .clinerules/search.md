# Search & Context Rules

## Environment
- All paths are Linux-based. Never assume macOS paths (no `/Users/`).
- The dev server runs on this i7 machine — it is not at `localhost` on the user's Mac.

## Reading Files
- Use `read_repo_file` only when you need to see the current contents of a file before editing it.
- The user will always tell you which file to work in. Do not search for files yourself.

## MCP Tool Call Format
All MCP tool calls MUST use this exact format:

```
<use_mcp_tool>
<server_name>context-engine</server_name>
<tool_name>read_repo_file</tool_name>
<arguments>
{"repo_name": "stoodleyweather", "relative_path": "src/lib/weather-utils.ts"}
</arguments>
</use_mcp_tool>
```

Do NOT use `<read_repo_file>...</read_repo_file>` or any direct XML tag format — it will not work.
