CodeGraph installed via npm (@colbymchenry/codegraph v1.6.0). Wired to Hermes. Run `codegraph init` in h-dashboard before code analysis tasks.
§
For h-dashboard PRs: user says 'pr' → create PR from current branch to upstream/beta (asgarimehdi/h-dashboard). All changes commit+push to current branch.
§
shadcn/improve skill loaded for h-dashboard — use for codebase audits and improvement plans. Do not execute without user request.
§
CodeGraph CLI must be installed (npm -g @colbymchenry/codegraph) AND `codegraph init` run inside h-dashboard before any code analysis. Config at ~/.hermes/config.yaml points the codegraph MCP at /home/runner/.npm-global/bin/codegraph.
§
Boost MCP occasionally dies on first stdio call ("lost its stdio subprocess") — just call it again. CLI fallback always works: php scripts/boost_tool.php <tool> '<json>'.
§
h-dashboard branch sydney tracks origin/beta (branch.sydney.merge=refs/heads/beta), so `git status` shows 'sydney...origin/beta' even when a same-named origin/sydney branch exists. Always use explicit refspecs HEAD:refs/heads/sydney.
§
MaryUI x-select defaults to optionValue='id'/optionLabel='name'. Options keyed 'value'/'label' need explicit option-value="value" option-label="label" or every <option> renders empty (blank control). Pass :options="$this->myOptions()" from a component method — a bare $myOptions is undefined in the Blade view.
§
scripts/e2e-test.sh has no `trap`: a failing run exits before teardown, leaving .env swapped to h_dashboard_e2e. Recover: `cp .env.dev.bak .env && rm -f .env.dev.bak`, then kill :8001 via `kill $(pgrep -f 'artisan serve')` — `pkill -f` kills the calling shell.
§
.env is gitignored. If lost, rebuild from `.env-example-github` + secrets in `.env.e2e`, override APP_URL=http://127.0.0.1:8000 and DB_DATABASE=h_dashboard, drop lines still containing `secrets.`, verify with `php artisan about --only=environment`.
§
`parse_ini_file('.env')` fails in h-dashboard (unquoted parens). Use a regex line scan or resolved config() when copying secrets between env files.