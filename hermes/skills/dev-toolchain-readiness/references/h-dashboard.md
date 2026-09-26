# h-dashboard Toolchain and Gates

Project-specific values for the dev-toolchain-readiness procedure. The repo's
`AGENTS.md` remains authoritative; this file records the probed working state.

## Working Branch and Remotes

- Canonical: `asgarimehdi/h-dashboard` (has the `beta` branch).
- Fork: `haileen5/h-dashboard`, configured as remote `origin` on this server.
- Current branch: `sydney`. Its tracking config points at `refs/heads/beta`
  (`branch.sydney.merge=refs/heads/beta`), so `git status` compares `sydney`
  against `beta` even though a same-named `origin/sydney` exists. Always use the
  explicit refspec `HEAD:refs/heads/sydney` for push, and `git branch -vv` to
  read the real tracking state.
- Sync order that works: canonical `beta` → fork `beta` → remote `sydney` →
  local branch. Fetch canonical into a temp ref (`refs/sync/canonical-beta`),
  verify the SHA against `ls-remote`, push to the fork with an explicit
  refspec, then merge down the chain.
- `.hermes.md` is tracked on `beta` and is commonly present as an untracked
  local copy; it will abort the merge until reconciled.

## Required Tools (probed working state)

| Tool | How to verify | Notes |
|---|---|---|
| Laravel Boost | `application_info` MCP call | stdio server may drop the first call; a second call reconnects. CLI fallback: `php scripts/boost_tool.php <tool> '<json>'` |
| Context7 | `query_docs` MCP call | needs an `/owner/repo` id. Resolve with `resolve_library_id` first (it also requires a `query` argument), then query. Laravel 13 resolves to `/websites/laravel_13_x` |
| GitHub MCP | `list_commits` on `asgarimehdi/h-dashboard` | large results spill to a file; read the spillover path rather than re-requesting |
| CodeGraph | `codegraph query "<Class>" --limit 5` in the repo | binary is a global npm package AND requires a per-repo `codegraph init`; without the index every query reports "not initialized" |

CodeGraph install/init when missing:

```bash
npm install -g @colbymchenry/codegraph@latest
cd <project> && codegraph init && codegraph status .
```

## Verification Gates

Run in this order before pushing. Prerequisites: the PostGIS/Redis compose
stack up, and the test database created from `template_postgis`.

```bash
vendor/bin/pint --test                    # formatter, must pass
vendor/bin/phpstan analyse --no-progress  # static analysis, no errors
XDEBUG_MODE=off vendor/bin/pest --parallel # full suite
```

For a targeted re-run of specific files, clear the Laravel caches first
(config and route), otherwise stale cached routes and config produce spurious
Livewire 404s and database-connection failures that look like real breakage.

## Testing Notes

- `InteractsWithTestSetup` shared trait provides user/unit/lookup seeding for
  new Feature tests; follow existing test files rather than hand-rolling setup.
- After seeding rows with explicit ids in Postgres, resync the sequence.
- A full parallel run takes roughly two to three minutes; run it in the
  background and continue with other work.
