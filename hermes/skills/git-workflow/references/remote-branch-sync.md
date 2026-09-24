# Remote Branch Synchronization

## When to Use

Use this recipe when a working branch on a fork must receive canonical `beta` updates, especially when the current branch tracks a differently named branch, the fork has diverged, or a push would otherwise be non-fast-forward.

Reusable sequence for a current branch on a fork that must receive canonical `beta` updates. Replace placeholders from the repository's actual Git configuration; never guess a remote name, branch name, or URL.

## Preflight

```bash
git status --short --branch
git remote -v
git branch -vv
git config --get-regexp '^(remote|branch)\.'
```

Record the current branch:

```bash
CURRENT_BRANCH=$(git branch --show-current)
```

Identify the fork remote and canonical source from the URLs. If the canonical source is not already a remote, use its URL only for a temporary fetch; do not add or rewrite remotes.

## Verify canonical beta

```bash
git fetch <canonical> beta:refs/sync/canonical-beta
git ls-remote <canonical> refs/heads/beta
git rev-parse refs/sync/canonical-beta
```

The local temporary ref and `ls-remote` SHA must match. Do not push an unverified ref.

## Synchronize the fork beta

```bash
git push <fork> refs/sync/canonical-beta:refs/heads/beta
git fetch <fork> beta
git rev-parse refs/remotes/<fork>/beta
```

Verify the fetched tracking ref equals the canonical temporary ref. If the fork's `beta` has a protection rule, stop and report the exact push rejection rather than changing its configuration.

## Integrate the current branch safely

Fetch both the fork's same-named current branch and its `beta` tracking ref:

```bash
git fetch <fork> \
  "refs/heads/$CURRENT_BRANCH:refs/remotes/<fork>/$CURRENT_BRANCH" \
  beta
```

Inspect divergence before merging:

```bash
git rev-list --left-right --count \
  "refs/remotes/<fork>/beta...HEAD" \
  "refs/remotes/<fork>/$CURRENT_BRANCH...HEAD"
git log --oneline HEAD.."refs/remotes/<fork>/$CURRENT_BRANCH"
```

If the remote current branch has unique commits, merge it without force:

```bash
git merge --no-ff --no-edit "refs/remotes/<fork>/$CURRENT_BRANCH"
```

Resolve conflicts semantically. For each conflict, compare the base, current, and incoming file, not just the conflict markers. Preserve valid local behavior and discard incoming changes that introduce undefined variables, stale test setup, or other semantic regressions. After editing:

```bash
git diff --check
php -l <changed-php-file>
git add <resolved-files>
git diff --cached --check
```

Never use `--ours` or `--theirs` as a substitute for reading the conflict. If the remote branch is a deliberate, already-reviewed replacement, that decision must be explicit.

## Merge synchronized beta

Preflight first:

```bash
git merge-tree --write-tree --messages HEAD refs/remotes/<fork>/beta
```

A zero exit code and no conflict messages is a useful preflight, not a substitute for a real merge. Then:

```bash
git merge --no-edit refs/remotes/<fork>/beta
```

Run the smallest test set covering the merge and any behavior changed by the branch update. For a Laravel application, clear config/routes first when required by the project instructions, then run the affected Pest files. Also run static/style checks required by the repository.

## Push and verify

Use an explicit destination so a tracking branch pointing at `beta` cannot redirect the push:

```bash
git push <fork> "HEAD:refs/heads/$CURRENT_BRANCH"
git fetch <fork> "$CURRENT_BRANCH" beta
git status --short --branch
git rev-parse HEAD
git rev-parse "refs/remotes/<fork>/$CURRENT_BRANCH"
git rev-parse refs/remotes/<fork>/beta
```

Done means:

- `HEAD` and the remote same-named branch have the same SHA.
- The current branch contains the synchronized `beta` history.
- No unmerged paths, conflict markers, unstaged changes, or unexpected submodule entries remain.
- `git remote -v` and the current branch name are unchanged.
- The push used a normal fast-forward update; no force push was required.

## Troubleshooting decision points

- **Non-fast-forward:** fetch the remote same-named branch, inspect its unique commits, merge it, rerun tests, then push normally.
- **Merge conflicts:** inspect all three stages and run the affected tests after resolution; do not choose a side reflexively.
- **Tracking shows `beta`:** inspect `git branch -vv`; use explicit `HEAD:refs/heads/$CURRENT_BRANCH` refspecs.
- **Canonical and fork beta differ:** compare the exact SHAs and commits; update the fork beta only after the canonical SHA is verified.
- **Working tree already has changes:** record the diff first, determine whether it belongs to the synchronization, and preserve unrelated changes. Do not reset or stash them away without an explicit reason.
