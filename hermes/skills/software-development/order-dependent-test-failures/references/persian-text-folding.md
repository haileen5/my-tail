# Persian/Arabic text folding: why a name becomes invisible to its own filter

A normalizer rewrites the *search term*; the stored text keeps its original code
points. `LIKE` then compares two different spellings and silently returns
nothing. Nothing errors, no row is marked invalid, the table just comes up
short. This is one cause of intermittent and order-dependent search failures
alongside the cache and faker causes in the parent skill.

## The two shapes that break it

Both are everyday Persian, which is why fixtures hit them only sometimes:

- **ZWNJ** (U+200C) → space. Stored `حرفه‌ای` keeps the ZWNJ; the term becomes
  `حرفه ای`.
- **Arabic Alef variants** آ/أ/إ (U+0622 / U+0623 / U+0625) → ا (U+0627).
  Stored `آموزش` keeps the آ; the term has ا.

## You cannot fix it in the pattern

PostgreSQL `LIKE` supports only `%` and `_` as wildcards and has **no
character-class syntax** — `[ ... ]` is matched literally. So a "match either
spelling" pattern is not expressible, and that version compiles, runs, and
matches nothing. Check the PostgreSQL 9.7 "Pattern Matching" documentation
rather than trusting memory here.

`regexp_replace` is the documented way to change the text being compared:

```php
// apply the SAME map the PHP side uses, then compare against the folded term
$expr = "regexp_replace({$column}, '[{$zwnj}{$zwj}]', ' ', 'g')";
foreach (self::charMap() as $from => $to) {
    if ($to !== ' ') { $expr = "regexp_replace({$expr}, '{$from}', '{$to}', 'g')"; }
}
return "regexp_replace({$expr}, ' +', ' ', 'g')";
```

## Two mistakes that each look like progress

- **Replacing ZWNJ with `''` eats the next letter.** `حرفه‌ای` collapses to
  `حرفهای` because the regex takes the following character as a modifier.
  Replace with a SPACE, then collapse runs with `' +' → ' '`.
- **Folding each space-mapped character with its own class also collapses the
  real spaces** in a name. Fold ZWNJ and ZWJ in one pass.

A refinement that *raises* the failure count is the signal that the approach is
wrong — revert rather than layering another variant on top of it.

## Not a performance regression

`LIKE '%term%'` was never index-seekable, so folding the column costs nothing in
the query plan. State this explicitly when proposing it, because "it makes the
query slower" is the obvious objection.

## Keep one source of truth for the map

Put the character map in one place and build both the PHP and the SQL side from
it, or they drift and the bug returns for a new character.

Implementation trap: a **trait constant cannot be read from outside the trait**
(`Cannot access trait constant`), and tests commonly call these helpers on the
trait directly. Use `public static function charMap(): array` instead of a
constant. In a trait, `self::` resolves to the trait, so the method works from
both a using class and the trait itself. Give it a `@return array<string, string>`
docblock or static analysis flags the missing value type.

## Prove it by printing code points, not glyphs

The two strings look identical in a terminal, which is why this takes so long to
see:

```php
implode(',', array_map(fn ($c) => dechex(mb_ord($c, 'UTF-8')),
    preg_split('//u', $value, -1, PREG_SPLIT_NO_EMPTY)))
```

Stored value with `200c` against a term with `20` is the finding. Also assert the
row count before and after the filter: `total: 1` unfiltered and `total: 0`
filtered with correct data means the *query* is wrong, not the fixture — that
pair of numbers moves you straight to the cause.

## Expect the tool-level false positive

Writing the very character you are debugging into a docs file (showing ZWNJ in a
worked example) can trip content filters that read the file as untrusted input.
The warning is right that invisible characters are present and wrong to conclude
injection. Scan for `Cf`/`Co`/`Cs` categories and bidi marks to confirm the file
is otherwise clean, then say so explicitly — including that the characters were
yours and that the file was left unmodified.
