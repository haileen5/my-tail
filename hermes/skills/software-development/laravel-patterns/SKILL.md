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

## Pitfalls

### PostgreSQL `interval` with bind parameters

`interval ?` does NOT work — PostgreSQL parser requires a string constant after
`interval`. Error: `syntax error at or near "$N"`. Use `make_interval()` instead.

### Empty ID array

`= ANY('{}')` returns zero rows (correct behavior). If `$ids` could be empty,
guard before the query or let the empty array naturally produce zero results.

### `IN (...)` vs `= ANY(?)`

`IN (...)` requires string interpolation or `?` per element. `= ANY(?)` with a
PostgreSQL array literal is cleaner and scales to any array size.
