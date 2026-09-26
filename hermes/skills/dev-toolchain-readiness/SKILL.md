---
name: dev-toolchain-readiness
description: "Verify mandated dev tools actually work before using them."
version: 1.0.0
author: Sydney
license: MIT
metadata:
  hermes:
    tags: [toolchain, mcp, readiness, verification, setup, gates]
    category: software-development
---

# Dev Toolchain Readiness

A tool that is *configured* is not a tool that *works*. MCP entries in
`~/.hermes/config.yaml` can name a binary that was never installed, an index
that was never built, or a library-id format the server rejects. The only proof
is one successful call per tool.

Use this when a project mandates specific tools (MCP servers, CLI code indexers,
linters) and before gating any push on the repo's own verification commands.

## When to Use

- A session opens on a project that names required dev tools, MCP servers, or a
  code indexer, and dependent work is about to begin.
- Before pushing a sync, merge, or batch of changes that the repo's own checks
  (formatter, static analysis, test suite) are expected to gate.
- After an environment change, when a tool that previously answered now returns
  nothing or a transport error.

## Standing Rules

- A tool is READY only after one real invocation returns real data. Config
  presence, an `enabled: true` flag, or a `which` hit on a wrapper script is not
  proof.
- Verify every mandated tool before starting dependent work, and report the
  status of each one — including the ones that needed fixing.
- When a tool fails from missing setup, capture and apply the FIX (install
  command, init step, config key), never a standing claim that the tool is
  broken. Environment state is the user's to fix, not a durable constraint.
- Never fake a tool result. If a server cannot be made to answer, say so and
  name the fallback path you did use.

## Procedure

1. **Read the project's agent instructions first.** They enumerate the required
   tools and the repo's own verification commands. Required tools are usually
   listed there; the project's `AGENTS.md` is authoritative over any guess.

2. **Probe each tool with the smallest real call**, in parallel where
   independent. A probe that returns data or a well-formed error proves the
   transport; a probe that never returns proves nothing. Examples:
   - MCP: call one cheap tool (`application_info`, `list_commits`, `query_docs`).
   - CLI: `--version`, then one real query against the project.

3. **Fix what is not ready**, in this order of preference:
   - Missing binary on PATH → install it, then re-probe.
   - Tool present but empty results → run its per-project index/init step, then
     re-probe. A code indexer that is installed but uninitialized answers every
     query with "not initialized".
   - Server drops its transport on the first call → call it again once; stdio
     servers commonly reconnect on the next request. If it stays down, use the
     project's documented CLI entry point for the same tool.

4. **Check argument contracts against the tool's own schema**, not memory.
   Servers that resolve identifiers separately (e.g. a docs server that wants
   `/owner/repo`) reject a bare name with a format error that names the expected
   shape. Run the resolve step first, then query with the returned id.

5. **Run the repo's verification gates in cost order** before pushing anything:
   formatter check → static analysis → targeted test files for the changed
   area → full suite in the background while you finish other work.

## Triage: one failing test after a merge

- Re-run the failing file **alone** first. Passes in isolation points at
  parallel-ordering or shared-state flake, not at the merge.
- Confirm with a **second full-suite run** before calling anything a
  regression. One flaky failure in a green-then-red-then-green cycle is not
  evidence.
- Only after a reproduced-in-isolation failure should you treat the merge as
  the cause and read the diff semantically.

## Pitfalls

### Verified late = the work was done blind

Probing tools after the edits and tests means a broken index or an unusable
docs server invalidated decisions already baked into the code. Probe first;
the checks are cheap and parallel.

### An "enabled" MCP entry that never answers

Config lists a command; whether that command exists on disk is a separate fact.
An entry whose command path no longer resolves fails at call time, not at
startup — so the config can look perfect while every call errors.

### A tool that returns empty rather than erroring

Worse than a hard error, because it reads as a legitimate negative result. If a
query returns "not found"/"not initialized", verify the index exists before
believing the answer.

### One failed test read as a regression

A parallel suite shares state across workers; a single failure that vanishes on
re-run is a known hazard. Treat a failure as real only after it reproduces.

See `references/h-dashboard.md` for the concrete toolchain and gates of the
h-dashboard Laravel project.
