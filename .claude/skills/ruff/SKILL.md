---
name: ruff
description: Format source code with ruff. Use when the user asks to format, lint, or fix code style.
---

Format and lint the project's Python source code using ruff.

Steps:
1. Run `ruff format` on the target path (default: `src/` and `tests/`)
2. Run `ruff check --fix` on the same path to auto-fix any lint violations
3. If any issues remain that ruff could not fix automatically, list them clearly

Use the Bash tool to run the commands. Default target when the user doesn't specify a path:
```
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
```

If the user specifies a file or directory, use that as the target instead.

When done, report:
- How many files were reformatted (from `ruff format` output)
- Any lint issues that were fixed automatically
- Any remaining issues that require manual attention
