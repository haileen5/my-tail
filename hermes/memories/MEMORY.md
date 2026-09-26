For h-dashboard PRs: user says 'pr' → create PR from current branch to upstream/beta (asgarimehdi/h-dashboard). All changes commit+push to current branch.
§
shadcn/improve skill loaded for h-dashboard — use for codebase audits and improvement plans. Do not execute without user request.
§
CodeGraph: npm -g @colbymchenry/codegraph, MCP wired in ~/.hermes/config.yaml → /home/runner/.npm-global/bin/codegraph; run `codegraph init` in h-dashboard before code analysis.
§
Boost MCP occasionally dies on first stdio call ("lost its stdio subprocess") — just call it again. CLI fallback always works: php scripts/boost_tool.php <tool> '<json>'.
§
h-dashboard branch sydney tracks origin/beta (branch.sydney.merge=refs/heads/beta), so `git status` shows 'sydney...origin/beta' even when a same-named origin/sydney branch exists. Always use explicit refspecs HEAD:refs/heads/sydney.
§
MaryUI x-select defaults to optionValue='id'/optionLabel='name'. Options keyed 'value'/'label' need explicit option-value="value" option-label="label" or every <option> renders empty (blank control). Pass :options="$this->myOptions()" from a component method — a bare $myOptions is undefined in the Blade view.
§
scripts/e2e-test.sh is NOT concurrency-safe and has no trap: two instances overwrite each other's .env.dev.bak with ALREADY-SWAPPED content, so restore writes e2e config back, bak vanishes, :8001 orphans. Never run two instances (incl. cron agents). After ANY run verify `grep DB_DATABASE .env` == h_dashboard. If bak lost: cp .env.e2e .env then set APP_URL=http://127.0.0.1:8000 + DB_DATABASE=h_dashboard; kill :8001 via `kill $(pgrep -f 'artisan serve --port=800[1]')` — never pkill -f 'artisan serve' (kills shared :8000). phpunit.xml pins h_dashboard_test, so suite results stay valid despite .env swaps.
§
.env is gitignored. If lost, rebuild from `.env-example-github` + secrets in `.env.e2e`, override APP_URL=http://127.0.0.1:8000 and DB_DATABASE=h_dashboard, drop lines still containing `secrets.`, verify with `php artisan about --only=environment`.
§
`parse_ini_file('.env')` fails in h-dashboard (unquoted parens). Use a regex line scan or resolved config() when copying secrets between env files.