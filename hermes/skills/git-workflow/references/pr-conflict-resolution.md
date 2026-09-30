# Resolving a conflicting open PR — command sequence

Companion to "Resolving a conflicting open PR" in SKILL.md. Assumes `gh` is
authenticated and remotes are already identified (see
`references/remote-branch-sync.md`).

## 1. Diagnose before touching files

```bash
gh pr view <n> --repo <base-owner>/<repo> --json mergeable,mergeStateStatus,files,statusCheckRollup
git fetch <canonical> pull/<n>/head:pr<n>          # PR refs live on the RECEIVING repo
git fetch <canonical> <target>
BASE=$(git merge-base pr<n> <canonical>/<target>)
git log --merges $BASE..<canonical>/<target>       # what merged since the PR branched
git merge-tree --write-tree --messages $BASE pr<n> <canonical>/<target>
```

Read the PR body first: authors usually name the competing PRs that will
supersede them. Decide **per conflicted file** whose version ships — the side
whose fix is a superset AND already merged into the target wins.

## 2. Resolve in a worktree, then prove it

```bash
git worktree add /tmp/pr<n> pr<n>                  # main clone's branch stays untouched
cd /tmp/pr<n>
git merge <canonical>/<target>                    # conflicts stop here
git checkout --theirs path/to/superseded-file && git add path/to/superseded-file
git diff <canonical>/<target> -- path/to/superseded-file   # MUST be empty
git diff <canonical>/<target> -- phpstan-baseline.neon     # derived files match the winner
git commit --no-edit
```

A baseline / config / error-count file keyed to the dropped code must equal
the target's version too, or static analysis fails on the merged tree.

## 3. Re-align tests and docs (follow-up commit)

- Assertions that still hold: keep unchanged.
- Assertions encoding the superseded behavior: rewrite to the semantics that
  actually ship.
- Stale prose claims in the PR's own docblocks or gotcha rows: fix now —
  otherwise the PR ships tests that fail and docs that lie.

## 4. Gates on the merged tree

A worktree has no untracked files (.env, vendor, node_modules), so tests run
only after removing it and checking the branch out in the main clone (one
worktree per branch):

```bash
git worktree remove /tmp/pr<n>
git checkout pr<n>
# project gates: feature tests + the target's coverage of the same area,
# formatter, static analysis
```

A green run from before the merge proves nothing about the merged tree.

## 5. Deliver, respecting permissions

```bash
gh api repos/<head-fork> --jq .permissions    # maintainerCanModify helps only
                                              # base-repo collaborators; check push
git push <own-fork> pr<n>:refs/heads/<same-branch-name>
gh pr create --repo <base-owner>/<repo> --base <target> \
  --head <you>:<branch> --title "..." --body "Replaces #<n> — <why>"
gh pr comment <n> --repo <base-owner>/<repo> --body "Superseded by #<m> ..."
```

- `push:false` on both the head fork and the base repo → the original PR head
  cannot be updated; open the replacement PR instead.
- `gh pr close --comment` fails without close permission while
  `gh pr comment` works for any authenticated account — split them, and hand
  closing the old PR to the user.
- After creating the replacement, verify with a fresh read, not the creation
  output: `gh pr view <m> --json mergeable,mergeStateStatus` (expect
  `MERGEABLE`) and poll `gh pr checks <m>` until every job concludes — some
  jobs (mutation testing) run 15–20 min on this repo.
