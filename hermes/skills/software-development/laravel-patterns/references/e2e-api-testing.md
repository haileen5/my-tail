# E2E API Testing with Playwright

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

## Key points

- Login happens in `beforeAll` (once per describe block), not per test.
- Cookies are serialized as `name=value` pairs joined by `; `.
- The `request` fixture (from Playwright) uses the same `baseURL` as page tests.
- For Sanctum session auth, the cookie is the session cookie.
- For Sanctum token auth, use `Authorization: Bearer <token>` header instead.
