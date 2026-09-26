---
name: postgres-persian-search
description: Use when Persian text search misses stored rows.
---

# Persian search in Postgres: fold the COLUMN, not the pattern

`normalizeForQuery()` rewrites the search term, but the stored text keeps the original code points, so `LIKE` silently stops matching. Two shapes break it, both everyday Persian:

- **ZWNJ** (U+200C) → space. `حرفه‌ای` is stored with the ZWNJ, searched as `حرفه ای`.
- **Arabic Alef variants** آ/أ/إ (U+0622/0623/0625) → ا (U+0627). `آموزش` is stored with آ, searched with ا.

A unit becomes invisible to its own name filter. Nothing errors.

## Why you cannot fix it in the pattern

PostgreSQL `LIKE` supports only `%` and `_`. It has **no character-class syntax** — `[ ... ]` is matched literally, so a "match either spelling" pattern is not expressible. This is the trap: the intuitive fix compiles, runs, and matches nothing.

Verify against the docs (PostgreSQL 9.7 "Pattern Matching"), not memory. `regexp_replace` is the documented way to change the text being matched.

```php
// apply the SAME map normalize() uses, then compare against the folded term
$expr = "regexp_replace({$column}, '[{$zwnj}{$zwj}]', ' ', 'g')";
foreach (self::charMap() as $from => $to) {
    if ($to !== ' ') { $expr = "regexp_replace({$expr}, '{$from}', '{$to}', 'g')"; }
}
return "regexp_replace({$expr}, ' +', ' ', 'g')";
```

## Two mistakes that each cost a round

- **Replacing ZWNJ with `''` eats the next letter.** `حرفه‌ای` collapses to `حرفهای` — the regex takes the following character as a modifier. Replace with a SPACE, then collapse runs with `' +' → ' '`.
- **Folding each space-mapped char separately breaks names.** Treating ZWNJ and ZWJ as separate `[ \t]` classes collapses unrelated runs. Fold them in one pass.

## Not a performance regression

`LIKE '%term%'` was never index-seekable, so folding the column costs nothing new.

## Keep one source of truth

Put the map in one place and build both sides from it. A trait **constant** cannot be read from outside the trait (`Cannot access trait constant`), and the tests call these helpers on the trait directly — use a `public static function charMap(): array` instead. In a trait, `self::` resolves to the trait, so this works from both a using class and the trait itself.

## How this presents as a "random" test failure

It looks like a flake because only some fixture names contain ZWNJ or آ. With random execution order you get a low but steady failure rate, and single-file reruns pass. Reproduce deterministically with fixed seeds rather than re-running:

```bash
for seed in $(seq 1 20); do
  php artisan test path/to/Test.php --order-by=random --random-order-seed=$seed
done
```

## When you prove it

Print the code points, not the glyphs — they look identical:

```php
implode(',', array_map(fn ($c) => dechex(mb_ord($c, 'UTF-8')),
    preg_split('//u', $value, -1, PREG_SPLIT_NO_EMPTY)))
```

If the stored value has `200c` and the term has `20`, you have it. Also assert the row count before and after the filter: `total: 1` unfiltered and `total: 0` filtered with correct data means the query, not the fixture, is wrong.
