# Verifying a Live Database After Data or Seeder Work

## When to Use

After any change to seeders, migrations, importers, or a manual data fix, and
before the commit/push/PR that the change is heading for — especially when the
request is phrased as "make sure nothing was lost in the database". Also use it
to answer "what state is this database in?" without trusting your own memory of
the writes you ran.

The gate this user asks for before any commit/push/PR that touches seeders or
data: prove nothing was lost or altered, then commit. Every check below is
read-only, so run them against production-shaped data — they are the evidence,
not a description of what the code is supposed to do.

## 1. Declared data vs. live rows

Diff what the seeder declares against what the table holds. Extract the seeder's
data array (eval the PHP array literal — regex it out of the file between its
`$x = [` marker and the statement that follows), key both sides by id, and
report four buckets:

```text
declared: 834      (what the seeder would insert)
in db   : 832      (what the live table holds)
missing in db (declared, absent): 2   <- rows only a fresh seed would create
mismatched fields: 0                  <- name/parent/type/region per id
in db but not declared: 0             <- rows nothing explains
```

- **mismatched** = a live row was edited by the app/user *or* your change
  overwrote it. Read each one before calling it expected.
- **in db but not declared** = rows your change orphaned or an older version
  created. Never dismiss this bucket as "legacy" without naming the producer.
- **missing** is acceptable only when you can name the mechanism that will
  create them (a fresh seed) and why the live DB does not have them.

## 2. Foreign-key orphans — zero is the number

One query, one row of results:

```sql
select
 (select count(*) from units u left join units p on p.id=u.parent_id
      where u.parent_id is not null and p.id is null) as orphan_parent,
 (select count(*) from units u left join unit_types t on t.id=u.unit_type_id
      where u.unit_type_id is not null and t.id is null) as orphan_type,
 (select count(*) from units u left join regions r on r.id=u.region_id
      where u.region_id is not null and r.id is null) as orphan_region,
 (select count(*) from persons p left join units u on u.id=p.u_id
      where p.u_id is not null and u.id is null) as orphan_person_unit;
```

Join on the column the row actually holds: link tables often key users to people
by a business key (`users.n_code`), not by `person_id`. Guessing the column
produces `Undefined table` / `column does not exist`, and a check you "fix" by
dropping the term has silently covered nothing.

## 3. Scope residuals must be enumerable

Query the condition your change was supposed to eliminate:

```sql
select count(*) from units where unit_type_id is null;   -- expect 0
select name from units where region_id is null;          -- expect a named list you can justify
```

A residual is acceptable only when every row in it is explainable by design
(a tree root has no parent region, so it has no county). "Probably fine" is not
the gate — print the names.

## 4. Catalog parity

Compare each seeded catalog against its seeder array, id by id: value tables
(id, name) and pivots (child, parent). Equal counts alone prove nothing — two
different tables of the same size both pass. Compare the sorted pair lists.

## 5. Table counts, before and after

A single row of counts across the tables your work could touch (units, types,
pivots, people, users, join rows, plus the feature's own tables) gives a cheap
regression signal and documents the state you are committing against.

## 6. Environment still points where you think

Any script that swaps `.env` for a test config can leave it swapped. Confirm the
live values before trusting any of the numbers above:

```bash
grep -E '^(DB_DATABASE|APP_URL|APP_ENV)' .env
```

## Order

Run 6 first (a wrong DB invalidates every other result), then 1–5, then commit
and push only with the outputs in hand. Report the numbers, not "everything
looks fine": a table of checks and their results is what makes the claim
verifiable.
