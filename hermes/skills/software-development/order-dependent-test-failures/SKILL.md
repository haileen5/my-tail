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
