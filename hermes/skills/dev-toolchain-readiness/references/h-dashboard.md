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
| GitHub MCP | `list_commits` on `asgarimehdi/h-dashboard` | large results spill to a file; read the spillover path rather than re-requesting. Needs `owner` and `repo` as separate fields — a joined `owner/repo` slug is rejected as missing. The MCP token can expire mid-session while the `gh` CLI stays valid; fall back to `gh` rather than declaring GitHub unreachable |
| CodeGraph | `codegraph query "<Class>" --limit 5` in the repo | binary is a global npm package AND requires a per-repo `codegraph init`; without the index every query reports "not initialized" |

CodeGraph install/init when missing:

```bash
npm install -g @colbymchenry/codegraph@latest
cd <project> && codegraph init && codegraph status .
```

Install into the same global prefix the `codegraph` MCP entry names in
`~/.hermes/config.yaml` (its `command`/`args` carry the absolute path), then
re-probe through that absolute path rather than through `which`. A package
that lands in a different prefix leaves the shell command *and* the configured
command both failing while the config still reads correctly. A successful
`init` reports indexed file/node/edge counts — treat a silent run as no proof.

## E2E (Playwright) Setup

`.env.e2e` is gitignored and may be absent, so a fresh machine needs it before
any E2E run:

```bash
bash scripts/build-env-e2e.sh                       # build it from .env.e2e.example
npx playwright install chromium                      # one-time browser download
psql -h 127.0.0.1 -U h_dashboard -d postgres \
  -c "CREATE DATABASE h_dashboard_e2e WITH OWNER=h_dashboard TEMPLATE=template_postgis;"
```

**Build `.env.e2e` in-shell, never by reading the value and rewriting it.** The
terminal masks secret values as `***` in command output, so a read-then-write
approach writes a literal `***` into the file and the app fails to boot with a
misleading key/credential error. Copy the values with `grep`/`cut`/`sed` inside
the shell and report only their *lengths* to confirm. A short `APP_KEY` (or any
value equal to `***`) is the tell.

Run through the wrapper, which swaps `.env` and restores it:

```bash
bash scripts/e2e-test.sh tests/e2e/<area>
```

The wrapper has no `trap`: a failing run leaves `.env` pointed at
`h_dashboard_e2e` with a `.env.dev.bak` beside it. `git status` showing an
unexpected `.env.dev.bak` means a run is in flight or aborted — restore it before
touching git state:

```bash
[ -f .env.dev.bak ] && cp .env.dev.bak .env && rm -f .env.dev.bak
```

Verify RED/GREEN by stashing only the source files, not the spec:

```bash
git stash push -- <source files>   # run the new spec, expect failure
git stash pop                      # restore, re-run, expect pass
```

A failing assertion burns its full timeout, and Playwright retries twice, so a
4-test RED run takes many minutes. Read `test-results/*/error-context.md` for the
captured DOM instead of waiting on stdout — and note that piping the run through
`grep | head` buffers all output until exit, so a background run looks empty
while it is progressing.

## Verification Gates

Run in this order before pushing. Prerequisites: the PostGIS/Redis compose
stack up, and the test database created from `template_postgis`.

```bash
vendor/bin/pint --test                    # formatter, must pass
vendor/bin/phpstan analyse --no-progress  # static analysis, no errors
XDEBUG_MODE=off vendor/bin/pest --parallel # full suite
```

Run `pint` *after* PHPStan when editing new PHP: Pint's reformat can introduce
fresh static-analysis findings, so the last writer is not the last checker.

For a targeted re-run of specific files, clear the Laravel caches first
(config and route), otherwise stale cached routes and config produce spurious
Livewire 404s and database-connection failures that look like real breakage.

## Testing Notes

- `InteractsWithTestSetup` shared trait provides user/unit/lookup seeding for
  new Feature tests; follow existing test files rather than hand-rolling setup.
- After seeding rows with explicit ids in Postgres, resync the sequence.
- A full parallel run takes roughly two to three minutes; run it in the
  background and continue with other work.
