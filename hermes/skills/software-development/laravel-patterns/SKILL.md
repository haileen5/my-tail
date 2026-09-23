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

### `IN (...)` vs `= ANY(?)`

`IN (...)` requires string interpolation or `?` per element. `= ANY(?)` with a
PostgreSQL array literal is cleaner and scales to any array size.

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

### Trait usage in test files

When migrating test files to a shared trait (e.g. `InteractsWithTestSetup`):
1. Add `use Tests\Support\Concerns\InteractsWithTestSetup;` import
2. Add `use InteractsWithTestSetup;` inside the class
3. Remove the local helper method entirely
4. Replace raw `DB::table()->insert()` + `setval()` with `$this->seedLookupTables()`
5. Update ALL call sites to match the trait's return signature
6. Remove unused `DB` and `Hash` imports only if no other code in the file uses them
