---
name: order-dependent-test-failures
description: Use when a test passes alone but fails in a suite.
version: 1.0.0
metadata:
  hermes:
    tags: [testing, flaky, isolation, cache, faker, parallel]
    related_skills: [systematic-debugging, test-driven-development]
---

# Order-dependent test failures

A test that passes in isolation and fails in a suite is not flaky — it is sharing
state with another test. The pass/fail split is a signal about *which* state, so
treat the split as the evidence, not the failure message.

## Reproduce deterministically first

Do not re-run the suite hoping to catch it. A low-rate order failure needs
hundreds of samples to hit by hand; fixed seeds give you a binary answer.

```bash
for seed in $(seq 1 20); do
  php artisan test path/to/Test.php --order-by=random --random-order-seed=$seed
done
```

Record which seeds fail. Re-run **without** `--parallel` to split the
candidate causes immediately — if it still fails serially, parallelism is
exonerated and you have not wasted a cycle on the most popular wrong theory.

## The isolation checklist, in the order that pays

Check these before forming any theory about the code under test. Each is cheap
and each has been the actual answer.

1. **Cache keys built from ids.** Postgres sequences are non-transactional, so a
   transaction-rollback fixture restarts ids at 1 on every test. Any key shaped
   `{prefix}:v{version}:{user_id}:{session_id}:{hash}` is then byte-identical
   across tests: the first test to run populates it and every later test reads
   a stale answer. Confirm by comparing the computed key across two tests
   rather than by reasoning about the cache backend.
2. **Static or class-level state.** Any `static` property, container singleton
   binding, or memoized property that outlives a single request.
3. **Random fixture values colliding with the assertion.** A factory drawing a
   random name can generate the very value the test filters on, so the test's
   own row satisfies a filter it is asserting is absent.
4. **Sequence values ahead of the table.** A rolled-back fixture leaves the
   Postgres sequence advanced while the table is empty again, so a seeder that
   inserts a catalog and a second seeder that references it by hardcoded id
   write N+1..N+22 while the pivot still points at 1..22 — a foreign-key
   violation that surfaces only when an earlier class consumed the sequence.
   Reset **every** table the `setUp` seeds, not only the one whose error you
   read: a setup that seeds two explicit-id catalogs plus an auto-increment
   seeder fails on whichever table it forgot, so the failing relation changes
   from run to run and looks like a different bug each time. Restart with
   `SELECT setval('tbl_id_seq', COALESCE((SELECT MAX(id) FROM tbl), 1), false)`:
   plain `setval(seq, 1)` uses `is_called = true`, so the next insert still gets
   id 2 and the same off-by-one reappears one row later, while
   `setval(seq, 0, false)` is rejected outright (a sequence value must be ≥ 1) —
   the `COALESCE(MAX(id), 1)` form is the one that works empty or not.

For each, the question is the same: does this value become *identical* between
two tests, or *collide* with what the assertion expects?

## Faking randomness out of a test is the wrong fix

When a fixture's random draw can match the filter under test, pin the values in
the test that needs determinism — do not change the factory. Factories encode a
distribution other tests may assert against, and narrowing it to fix one test
silently changes theirs. If a factory really is producing a bad value, fix it in
its own commit with its own test, not as a side effect of a flake fix.

## Verify the collision rate before believing it

Do not assume a rare random value is the cause. Sample the generator and count:

```bash
# measure, don't guess — sample the generator, count matches
for i in $(seq 1 3000); do ...; done | sort | uniq -c | sort -rn | head
```

A rate you can quote ("3/3000 for the exact name, 13/3000 for names containing
it") is a finding. "Faker sometimes does this" is a guess that ends in a factory
edit you cannot justify.

## Fix isolation at the base class, not per test class

A per-class fix only moves the failure to whichever class you missed. Any class
that builds the entities a cache key names can write that key, so the flush
belongs in the base `TestCase::setUp()`.

Ordering rule that makes this correct: a child class's `setUp()` runs
`parent::setUp()` first and seeds after, so a flush in the base class happens
*before* the child's seeders bump any version counter. One flush in the base
class therefore covers every class, and no test class needs to know about it.
Never flush inside a test method — the test that needs isolation is the one that
was already polluted.

## Prove the fix with repetition, not with one green run

A single passing run proves nothing about an order bug. Two gates:

```bash
# gate 1 — the reported tests, many orders
for seed in $(seq 1 20); do ... --order-by=random --random-order-seed=$seed; done
# gate 2 — the whole suite, repeatedly, in the runner that actually ships
for i in $(seq 1 10); do vendor/bin/pest --parallel || echo "RUN $i FAILED"; done
```

Run both against the final code, not against an intermediate revision — a green
result on superseded code is not evidence for what you are shipping.

## Get a clean baseline before blaming your diff

Dozens of failures across files your diff never touched are not yet evidence in
either direction. Stash everything including untracked files, run the same suite
on the clean tree, and diff the two failure sets:

```bash
git stash push -u -m wip
composer test > /tmp/baseline.log 2>&1
git stash pop
```

Only a failure present in your run and absent from the baseline is yours. Do the
same in reverse when your own new test fails inside a batch but passed alone —
that split points at shared state (checklist above), not at the assertion.

Adding, renaming or deleting a test file reseeds PHPUnit's shuffle, so a green
baseline next to a red diff-run can be pure order exposure. When the failure set
covers files your diff never touched, run both trees under the same fixed
`--order-by=random --random-order-seed=N` before theorising; a set that vanishes
on an unchanged tree is exposure, and you report it that way — not as a bug you
fixed. One green run of the same tree settles nothing either way.

## Running the gates at suite scale

A full suite outlives the 300s `execute_code` kernel cap, which kills the call
and takes its session state with it. Launch long runs with
`terminal(background=true)` writing to a log file, then block on
`process_manage(action='wait', session_id=..., timeout=...)` — each wait clamps
to ~180s, so poll until the process exits rather than trusting one long wait.

## Prove the fix with a test that asserts behaviour

Assert through the component or the service the user touches. Do not assert that
a cache key was poisoned and then ignored: that tests your own poison, not the
fix, and it passes in isolation while the real bug still ships.

## Documentation drifts toward the wrong fix

When you record the gotcha in an agent-instructions file, re-read the row
against the code you actually shipped. Advice phrased at the wrong level
("flush in `setUp` after the seeders", when the fix lives in the base class) is
a trap for the next session — it reads as authoritative and reintroduces the gap
you just closed. Prefer advice with no ordering rule attached.

Cross-references between rows are fragile in a table whose rows get inserted and
deleted; name the function instead of saying "the row above".

## References

- `references/persian-text-folding.md` — a normalizer that rewrites the term but
  not the stored column, so a row stops matching its own name. Why the
  pattern-side fix cannot work, and how to prove the fold by code point.

The standalone skill `postgres-persian-search` covers that same folding ground
and is not curator-managed, so it is left in place. Prefer this skill: it also
carries the cache-key and faker causes, which present as the same flaky tests.
The two do not conflict; they differ in scope.
