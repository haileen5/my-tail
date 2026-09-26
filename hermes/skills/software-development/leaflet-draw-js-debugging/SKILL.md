---
name: leaflet-draw-js-debugging
description: Use when Leaflet.Draw misbehaves but PHP tests pass.
---

# Debugging Leaflet.Draw on a real map

PHP tests cannot reach this code. Render the page in Chromium and read state out of `page.evaluate`; treat every theory about the DOM as a hypothesis until a probe prints it.

## Run E2E without re-seeding every time

`scripts/e2e-test.sh` re-seeds on every run (~10 min) and its teardown is skipped when Playwright fails. Bring the env up once, then iterate on plain `npx playwright test`:

```bash
cp .env .env.dev.bak && cp .env.e2e .env
php artisan config:clear && php artisan migrate:fresh --seed --force
php artisan serve --port=8001 &        # then: BASE_URL=http://localhost:8001 npx playwright test ...
```

Remember `APP_LOCALE=fa` — assert on the Persian labels the user actually sees.

## Wait for the map, not the network

`await networkidle` never fires: Leaflet keeps fetching tiles. Wait for `#unitMap` and `.leaflet-draw-edit-edit` to be visible instead. A blanket `waitForTimeout` only hides races.

## Leaflet ships minified

`layer.constructor.name` is `"e"`, never `"Polygon"`. Always compare against the real prototype:

```ts
allPolygons: layers.every((l) => l instanceof (window as any).L.Polygon)
```

Keep `typeNames` in the returned payload anyway so a failure prints what it actually got instead of a bare `false`.

## Failures that raise NO error

These are the ones that cost the most time — a green-looking edit that does nothing:

- **`L.Control.Draw({ edit: { featureGroup } })`** — `_checkDisabled` greys out edit/remove unless `featureGroup.getLayers().length > 0`. A layer added straight to the map is invisible to the toolbar.
- **`L.Edit.Poly` nesting** — `getLatLngs()` is `[ring]` for a plain polygon but `[[ring]]` for one built from MultiPolygon. Two levels is all `L.Edit.Poly` reads, so `editing.enabled()` returns `true` while `.leaflet-editing-icon` count is `0`. Probe the depth before assuming the layer is fine.
- **`fitBounds` on an empty layer** throws `Bounds are not valid` inside a `try/catch` and only `console.error`s — the toolbar just stays disabled. Read the browser console, not the test assertion.

## Normalise geometry at the boundary

```js
var ring = layer.getLatLngs();
while (Array.isArray(ring) && Array.isArray(ring[0])) ring = ring[0];
```

Without this, `ring.map(ll => [ll.lng, ll.lat])` walks arrays instead of LatLngs and yields `[undefined, undefined, ...]`.

## Check what the model actually returns

`ST_AsGeoJSON()` returns a **bare geometry** (`{type, coordinates}`) with no `geometry` key — not a Feature. In h-dashboard `Boundary::getGeojsonAttribute()` passes it straight through, so `L.geoJSON(data)` silently builds an empty feature. Confirm with the DB, not by reading the accessor:

```bash
php -r '… DB::selectOne("SELECT ST_AsGeoJSON(boundary) AS g FROM boundaries LIMIT 1")->g'
```

## Symptomless state bugs

If a save/delete handler branches on a truthiness check, verify the value is initialised on page load. `_mapGeojson` left `undefined` meant a plain "save" click fell through to the delete branch — the boundary was destroyed by doing nothing.

## TDD order that worked

1. Write the E2E spec.
2. `git stash` the fix, run once, confirm the failure names the real defect.
3. `git stash pop`, iterate with the fast loop above.
4. `vendor/bin/pint --dirty` and `vendor/bin/phpstan analyse` (both are fast) before committing.
