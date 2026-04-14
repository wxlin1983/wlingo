---
name: comment
description: Add or update code comments in English. Use when the user asks to add, update, improve, or write comments. Comments should be concise and must not change any program behavior.
---

Add or update comments in English following these rules:

1. **Concise** — one short phrase or sentence per comment; no filler words
2. **No behavior changes** — only add/modify comments, never touch logic, formatting, or structure
3. **Comment what's non-obvious** — skip comments that just restate the code (e.g. `i += 1  # increment i`)
4. **Use the file's comment style** — match existing comment syntax and placement conventions
5. **Function/class docstrings** — briefly describe purpose and any non-obvious parameters or return values; skip trivial ones
6. **Inline comments** — only for tricky logic, side effects, or domain-specific choices

When done, briefly list what was added or changed and why each was worth keeping.
