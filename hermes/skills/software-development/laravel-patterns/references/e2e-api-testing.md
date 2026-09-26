# E2E Testing with Playwright

## Pattern: Authenticate then call API endpoints

When E2E tests need to verify API responses (not just UI), authenticate via
the login page first, capture cookies, then use `page.request` or `request`
fixture with those cookies.

### Setup (beforeAll)

```typescript
test.describe('API endpoints', () => {
  let cookies: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await login(page);
    const context = await page.context();
    const cookieList = await context.cookies();
    cookies = cookieList.map((c) => `${c.name}=${c.value}`).join('; ');
    await page.close();
  });
```

### Making authenticated requests

```typescript
  test('GET /api/resource returns data', async ({ request }) => {
    const response = await request.get('/api/resource', {
      headers: { Cookie: cookies },
    });

    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.data).toHaveProperty('id');
  });
```

### Unauthenticated test

```typescript
  test('unauthenticated returns 401', async ({ request }) => {
    const response = await request.get('/api/resource');
    expect(response.status()).toBe(401);
  });
```

### Key points

- Login happens in `beforeAll` (once per describe block), not per test.
- Cookies are serialized as `name=value` pairs joined by `; `.
- The `request` fixture (from Playwright) uses the same `baseURL` as page tests.
- For Sanctum session auth, the cookie is the session cookie.
- For Sanctum token auth, use `Authorization: Bearer <token>` header instead.

## Pattern: durable page specs

Rules for UI specs against a live app. Each one replaces a failure mode that
costs a full suite cycle to discover.

### Wait with `expect()`, never fixed sleeps

`expect(locator).toBeVisible()/toContainText()` polls until its deadline and
therefore absorbs debounce windows, framework roundtrips, and slow CI runners.
`page.waitForTimeout(N)` is a bet on an N you cannot know: too short flakes,
too long burns minutes, and Playwright's retry only hides both. If a state
transition needs detection, assert the state (`not.toContainText(...)`), not
the clock.

### Anchor readiness on page text, not `networkidle`

`waitForLoadState('networkidle')` stalls on any stray request (analytics,
service workers, sockets) and tells you nothing about the app being usable.
In `beforeEach`, wait for a marker only this page renders:
`await expect(page.locator('body')).toContainText('Page title')` — it fails
fast when the page is broken instead of timing out generically.

### Assert the mechanism's fingerprint, not just the outcome

A test that only checks the final state passes when the feature is broken for
a different reason. Prefer an assertion nothing else on the page can produce:
a CSS class the code path under test is the only writer, a dispatched event, a
rendered value that had to travel through the wiring. If the candidate
assertion also holds on first paint or on the empty case, it discriminates
nothing — keep looking.

### Assert semantics, not count deltas

`expect(after).toBeGreaterThan(before)` passes whenever *anything* changed —
including the half-working behavior it was meant to rule out (an "expand all"
that restores only one level). Assert what the user sees: the deep node is
hidden after collapse, visible again after expand. Counts are evidence for
the report, not the assertion.

### Prove the fixture before asserting on it

Never assert a name/value the seed merely *might* contain. Read the actual
seeded data first — point the framework at the e2e database and dump the rows
(`DB_DATABASE=<e2e_db> php artisan tinker --execute='...'` for Laravel, or a
copy of the seeder) — then assert on what is really there. An assertion
against data that does not exist fails deterministically and teaches you the
fixture, not the bug. (Same rule as unit-test seeds: check, don't assume.)

### Run the suite where it can finish

- Seeded e2e runs (migrate:fresh + seed + serve + specs) exceed foreground
  command timeouts: launch as a background job with the completion-notification
  flag and let the notification bring the result.
- Sequence e2e with any other job that reads `.env`: the runner swaps env
  files, so a concurrent suite booted from a half-swapped env reads the wrong
  database. Run them one after the other in one job, not side by side.
- A runner with no exit trap leaves its env swap and its test-port server
  behind on failure. Restore the env backup and kill ONLY the test-port
  server (`kill $(pgrep -f '<server> --port=<test_port>')`); never
  `pkill -f <server>` — that takes the shared dev server down too.
