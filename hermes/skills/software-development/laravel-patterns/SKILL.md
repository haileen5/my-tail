---
name: laravel-patterns
description: "PostgreSQL parameterized queries and Laravel patterns."
version: 1.0.0
author: Sydney
license: MIT
metadata:
  hermes:
    tags: [laravel, postgresql, sql, security]
    category: software-development
---

# Laravel + PostgreSQL Patterns

Standing rules and patterns for Laravel projects using PostgreSQL.

## SQL Parameterization (PostgreSQL)

**Never interpolate variables into raw SQL strings — use bind parameters.**

### Array parameters with `= ANY(?)`

PostgreSQL's `= ANY(?)` accepts an array literal string as a bind parameter:

```php
// Build the array literal from a PHP array
$idArray = '{'.implode(',', array_map('intval', $ids)).'}';

// Use in query with bind parameter
DB::select('SELECT * FROM t WHERE id = ANY(?)', [$idArray]);
```

This replaces the fragile pattern of `IN ({$idList})` with string interpolation.

### Interval parameters — `make_interval()`, not `interval ?`

PostgreSQL's `interval` keyword requires a string constant, not a bind parameter.
`interval ?` throws `SQLSTATE[42601]: syntax error at or near "$N"`.

**Use `make_interval()` instead:**

```php
// WRONG — syntax error
DB::select("SELECT now() - interval ? || ' days'", [$days]);

// CORRECT
DB::select('SELECT now() - make_interval(days => ?)', [$days]);
```

`make_interval()` accepts bind parameters for years, months, days, hours, mins,
secs. Available PostgreSQL 12+.

### Binding arrays of integers

Cast each element with `intval()` before building the PostgreSQL array literal —
defense-in-depth on top of parameterization:

```php
$idArray = '{'.implode(',', array_map('intval', $accessibleIds)).'}';
```

## Pest / PHPUnit Coverage Annotations

Pest v4 removed `coversNothing()` as a standalone function. Only `covers()` exists
in `Pest\Functions`.

**Class-based tests** (extending `TestCase` directly): use PHPUnit attribute.
```php
use Tests\TestCase;

#[\PHPUnit\Framework\Attributes\CoversNothing]
class MyTest extends TestCase { ... }
```

**Pest-style tests** (using `uses()` / `test()` / `it()`): `coversNothing()`
also does NOT work — same function does not exist. Use `covers(SomeClass::class)`
or omit coverage annotation.

`covers(User::class)` works in both styles — it delegates to PHPUnit's
`#[Covers]` internally.

## Pitfalls

### Pest `coversNothing()` does not exist
`coversNothing()` is NOT a Pest function in v4. Calling it in a class-based test
yields `Call to undefined function`. Use `#[\PHPUnit\Framework\Attributes\CoversNothing]`
attribute above the class declaration instead. In Pest-style files, just omit the
coverage annotation or use `covers()`.

### PostgreSQL `interval` with bind parameters

`interval ?` does NOT work — PostgreSQL parser requires a string constant after
`interval`. Error: `syntax error at or near "$N"`. Use `make_interval()` instead.

### Empty ID array

`= ANY('{}')` returns zero rows (correct behavior). If `$ids` could be empty,
guard before the query or let the empty array naturally produce zero results.

### A raw joined column inside `update()`

Postgres gives a builder `update()` no FROM clause: a join compiles to
`UPDATE t SET c = <expr> WHERE ctid IN (SELECT ctid FROM t JOIN …)`, so
`DB::raw('other.col')` in the SET list names a relation that is out of scope →
`relation "other" does not exist`. Two shapes that work:

```php
// correlated subquery in SET — the join stays, but only decides WHICH rows
$n = DB::table('units')
    ->join('units as p', 'p.id', '=', 'units.parent_id')
    ->whereNull('units.region_id')
    ->whereNotNull('p.region_id')
    ->update(['region_id' => DB::raw(
        '(select q.region_id from units q where q.id = units.parent_id)',
    )]);

// or plain SQL with FROM — returns the affected row count directly
$n = DB::update('UPDATE units c SET region_id = p.region_id FROM units p
    WHERE c.region_id IS NULL AND p.id = c.parent_id AND p.region_id IS NOT NULL');
```

Keep the join (or the `FROM`-equivalent predicate): it limits the write to rows
whose source is non-null, and re-assigning a column to its own value still
counts as an affected row, so a "repeat until nothing changes" loop built
without it never terminates.

### A gate that checks zero files is not a gate

`pint --dirty` (what `composer pint` runs) inspects only modified files — on a
clean tree it passes while checking nothing, right after you committed the
failures. Run the command CI runs (`vendor/bin/pint --test`) and read its exit
code. Same principle for any linter/analyzer wrapper: a green wrapper that
examined zero files has verified zero.

### Baselines are line-keyed

A baseline entry embeds the line number of the error it suppresses, so
inserting even a comment above that line unmatches the entry and the run
reports `ignore.unmatched` errors that are not new bugs. After editing a
baselined file: regenerate with `--generate-baseline`, then verify the
baseline diff shows **0 additions** — any addition is a real new error being
suppressed. Regenerate to drop stale entries, never to absorb new ones.

### `IN (...)` vs `= ANY(?)`

`IN (...)` requires string interpolation or `?` per element. `= ANY(?)` with a
PostgreSQL array literal is cleaner and scales to any array size.

## Relations and Static Analysis

### Read a relation through the model, never through `->relation()->first()`

At PHPStan level 6 a relation method returns an untyped builder, so
`$unit->region()->first()->name` resolves to `Illuminate\Database\Eloquent\Model`,
which has no `name` — every property read becomes
`Access to an undefined property Model::$name`. Calling the relation as a query
also discards any eager-load, re-querying per row.

Use the loaded relation when the caller eager-loaded it, and fall back to the
model class (not the relation) otherwise:

```php
$region = $unit->relationLoaded('region')
    ? $unit->region
    : Region::query()->find($unit->region_id);

if (! $region instanceof Region) { /* ... */ }
```

The `instanceof` check is what narrows the type — dropping it re-triggers the
same error. Fix the underlying access, never a baseline entry or
`@phpstan-ignore`.

### Eager-load a relation the moment a new column reads it

Add a column that touches a relation (a region name, a type name) turns a
previously flat export/report into an N+1 unless the loader is updated in the
same change. Add the `with()` next to the relations already being loaded, and
say in the commit why.

### Eloquent query chains when PHPStan has no larastan

Without larastan the only type info is Laravel's own PHPDoc.
`Eloquent\Builder` declares `where()`, `get()`, `with()`, `first()` — but NOT
`whereIn()`, `limit()`, `take()`, `count()`. Those resolve through
`@mixin Query\Builder`, which retypes the rest of the chain as the query
builder: `->with()` becomes `Call to an undefined method Query\Builder::with()`
and `get()` reads back as `Collection<int, stdClass>` instead of your models.

Shape that stays clean at level 6:

```php
// IN-filters live inside where(Closure); the chain never leaves Eloquent\Builder
return Unit::query()
    ->with(['unitType'])
    ->where(function ($query) use ($ids) {
        $query->whereIn('id', $ids);
    })
    ->get();

// Row cap AFTER get(), never ->limit(N)->get()
$rows = $query->get()->take(20);
```

- Never add `@method static Builder whereIn()` to a model to silence a static
  `Model::whereIn()` call: the annotation is global — every `Model::whereIn()`
  chain repo-wide retypes and unmasks errors in files your diff never touched.
  Fix the chain in your own code instead.
- Static magic callables on the model — `Model::firstOrCreate()`,
  `updateOrCreate()`, `firstOrNew()` — go through `__callStatic` and report
  `Call to an undefined static method`. `Builder` declares them, so prefix with
  `query()`: `UnitType::query()->firstOrCreate(['name' => $name])` passes level
  6 unchanged.
- When the accepted shape is unclear, drop a throwaway class into an analyzed
  path, run the analyzer once, and read what it complains about — cheaper than
  theorizing about PHPDoc resolution. Delete the probe before committing.

## Adding a Row to a Seeded Catalog

Catalogs whose seeders comment each entry with its id, plus a pivot seeder that
hardcodes those ids, are three ordered edits:

1. **Append** the new value to the catalog seeder. Inserting mid-list shifts
   every id below it and silently re-points every hardcoded pivot row at the
   wrong value.
2. Add the pivot rows only after checking the id the value will actually get —
   a pivot pointing at an id the catalog never creates fails at seed time with
   a foreign-key violation, which reads like a data bug rather than an ordering
   one.
3. **Backfill rows that already exist**, because any seeder that creates missing
   rows on the fly (path-segment walkers, find-or-create importers) never
   revisits rows it inserted before the catalog entry existed. Fold the backfill
   into the seeder that already owns those rows — a private method called at the
   end of `run()` — rather than writing a new `XSeeder` class: seeders are the
   files that re-run, so a new class buys nothing but `DatabaseSeeder` wiring and
   a second entry point to maintain for one UPDATE. It still repairs a live
   database, because `php artisan db:seed --class=<that existing seeder>` re-runs
   it cheaply (its own row-skipping skips the heavy part); `firstOrCreate` for
   the catalog value keeps repeated runs from duplicating it.
   Do not offer "apply it once and delete the code" as an alternative: a data
   rule that only ran once is invisible to the next fresh seed.

4. **Prove the catalog covers every reference before deleting lazy creation.**
   When the rows currently created on the fly are moving into the catalog
   seeder, resolve the import data against the catalog FIRST: a short checker
   (eval the catalog array, walk each record's path matching name-within-parent)
   prints the exact segments a fresh seed would fail on. Add everything it
   reports in the same change — the moment the walker's create branch is gone,
   an unresolved segment changes from "silently created with no type/region" to
   a crashed seeder, and the checker is what turns a hunch into a list.

Verify on the live database afterwards with two counts: rows that received the
new value, and rows inside the target scope still missing it.

For the full pre-commit gate (declared-vs-live diff, FK orphans, scope
residuals, catalog parity, `.env` check) see
`references/data-integrity-verification.md` — run it before any commit, push or
PR that follows data work, and report the numbers rather than a verdict.

### A rule that covers a whole branch of a tree

When the rule is "this node and everything under it", do not recurse row by row
in PHP: resolve the roots by name, take the subtree in one call, update once,
and drive it from a map so the next rule is one array line.

```php
$rules = ['ستاد' => 'ستادی', 'فوریت' => 'فوریت']; // نام واحد => نوع واحد

foreach ($rules as $unitName => $typeName) {
    $rootIds = DB::table('units')->where('name', $unitName)->pluck('id')->all();
    if ($rootIds === []) { continue; }

    $typeId = UnitType::query()->firstOrCreate(['name' => $typeName])->id;

    DB::table('units')
        ->whereIn('id', Unit::descendantIds($rootIds))
        ->update(['unit_type_id' => $typeId]);
}
```

- `descendantIds()` includes the input ids and dedupes with `UNION`, so a
  `parent_id` cycle terminates instead of hanging the connection — never
  re-implement the walk with `UNION ALL`.
- Match roots by **exact** name, not `LIKE '%…%'`: one data row per rule keeps
  the update from reaching same-named units elsewhere that already carry a
  different type.
- Running the map after the rows are created makes one pass serve both a fresh
  seed and a database seeded before the type existed.

## Laravel Boost from the CLI

When no MCP transport is up, `php scripts/boost_tool.php <tool> '<json>'` bridges
the same tools:

- Argument key for queries is `query`, not `sql` — `"sql": "..."` is rejected
  with `Please pass a valid query`.
- `DatabaseQuery` is read-only (SELECT/SHOW/EXPLAIN/DESCRIBE). Writes go through
  `php artisan tinker --execute '...'` — single-quoted so the shell does not
  expand `$` or `!`.

## Changing the Shape of an Export or Report

### Adding a column breaks index-based test assertions

Tests that assert `$row[3]`, `$row[6]` silently mean something different after a
column is inserted mid-list — they fail with a value mismatch far from the cause,
or worse, still pass against the wrong field.

- Find them by grepping the test tree for the export class name, the column
  count, and the asserted literal values, not just for the heading strings.
- Prefer a heading→column-letter helper over raw indices, so later column
  additions do not shift unrelated assertions.
- When a column must read a *type* discriminator rather than a parent, write
  the test for the wrong-looking case explicitly. A column labelled for the
  narrower type must show a placeholder, never the wider type's value —
  repeating it is both wrong and defeats filtering, since one parent value
  swallows every row beneath it.

## Sortable List Pages (table header sorting)

### The requested `ORDER BY` must be the FIRST key, not a tie-break

`orderBy()` appends — it never replaces and never de-duplicates — so a list query
that starts from a default-order scope and then applies the user's column yields
`ORDER BY sort_order, id, name desc`: the clicked column runs only among rows
already tied on the earlier keys, i.e. **every header sort is a silent no-op**.
Postgres does not collapse the repeated `id` either, so `ORDER BY id asc, id desc`
keeps the first direction and a descending click on the key column does nothing.

- Build the list query WITHOUT the default-order scope, apply the requested
  column as the first `orderBy`, then add the default scope's columns back as an
  explicit tie-break (`if ($column !== 'id') { $query->orderBy('id'); }` — skip
  the key being sorted, or its duplicate cancels one direction).
- Keep the component's default `sortBy` equal to the scope's first key, so the
  untouched page renders in exactly the order it did before.
- Diagnosis before fix: print `toSql()` on the real chain — the ORDER BY clause
  shows the precedence directly, and a UI "sort does nothing" is a server-side
  ordering problem, not a Livewire event problem. In MaryUI the header click is
  just `$wire.set('sortBy', {column, direction})` (sortable defaults to true once
  `sortBy` is non-empty), so the property does update; only the SQL is wrong.

### Prove a sort with fixtures where the two orders disagree

A sort test whose fixture is ordered the same way by both the default and the
requested key passes against the broken query. Give `sort_order` an order that
contradicts the key under test (ascending `sort_order` vs. descending `id`) so the
wrong query can only produce one answer and the right query the other, then assert
the row ids:

```php
$ids = Livewire::test('it.zabbix-devices')
    ->set('sortBy', ['column' => 'id', 'direction' => 'desc'])
    ->viewData('devices')   // data returned by the component's with()
    ->pluck('id')->all();
expect($ids)->toBe([$newer->id, $older->id]);
```

`Testable::viewData()` reads the data the component passes to its view (the
`with()` array), which is otherwise unreachable from a test — `get()` only reads
public properties. Pin a second test on the DEFAULT order as well, so dropping
the default scope later cannot silently change the untouched page.

## Laravel Testing Patterns

### Associative array destructuring from traits

When a shared trait returns an associative array (e.g. `['user' => $user, 'unit' => $unit]`),
destructure with named keys — not numeric indices:

```php
// WRONG — tries index 0 and 1, gets nothing
[$user, $unit] = $this->createUserWithUnit(['permission']);

// CORRECT — matches array keys
['user' => $user, 'unit' => $unit] = $this->createUserWithUnit(['permission']);
```

PHP numeric destructuring (`[$a, $b] = ...`) accesses by integer index, not by
key name. Associative arrays returned by factories/traits have named keys.

If only one value is needed, destructure just that key:
```php
['user' => $user] = $this->createUserWithUnit(['permission']);
```

### Assertions must fail when the feature is broken

A test that stays green with the feature broken is worse than no test — it
buys confidence. Common shapes of vacuous assertion, and the fix:

- **Asserting the input, not the output.** Reading a component property you
  just passed in (`get('personCounts')`) proves nothing travelled anywhere.
  Mount the component that does the wiring and assert the RENDERED result
  (`assertSee('1 نفر')`) or the dispatched event.
- **A substring that also matches the empty case.** `assertSee('نفر')` passes
  for "0 نفر"; assert the number or the full expected string, not the label.
- **Re-pointing the mount at a smaller component.** Moving a test from the
  page to a bare child silently drops the page-level wiring it was guarding —
  keep the mount target that exercises the contract under test.
- **Deleting a test instead of updating it.** Allowed only when the code path
  it guarded is gone; if the path still exists (a per-node query, an N+1
  window), rewrite it against the new home — shared traits usually already
  have the helper (`assertNoNPlusOne`, `assertQueryCount`).
- **A delta that any partial behavior satisfies.** `expect(after).toBeGreaterThan(before)`
  stays green when a "expand all"-style action restores only one level of the
  tree it promises to open. Assert the semantic outcome instead: the deep node
  is hidden after collapse, visible again after expand.

Before committing a tightened assertion, check the seed/fixtures actually
contain what it demands — an assertion against data that does not exist fails
deterministically and wastes a full CI cycle to discover the fixture, not the
bug.

### Trait usage in test files

When migrating test files to a shared trait (e.g. `InteractsWithTestSetup`):
1. Add `use Tests\Support\Concerns\InteractsWithTestSetup;` import
2. Add `use InteractsWithTestSetup;` inside the class
3. Remove the local helper method entirely
4. Replace raw `DB::table()->insert()` + `setval()` with `$this->seedLookupTables()`
5. Update ALL call sites to match the trait's return signature
6. Remove unused `DB` and `Hash` imports only if no other code in the file uses them
