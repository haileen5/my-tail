---
name: git-workflow
description: "Git pitfalls: remotes, branch sync, staging, identity."
version: 1.0.0
author: Sydney
license: MIT
metadata:
  hermes:
    tags: [git, workflow, pitfalls, staging, nested-repos, commit]
    category: software-development
---

# Git Workflow

Pitfalls and procedures for everyday git operations that fall outside standard
`gh` CLI workflows (for gh-specific flows see the `github` skill).

## Standing Rules

- Always check `git status` and `git remote -v` before staging or pushing.
- Configure per-repo identity before first commit if global config is absent.
- Never assume a branch name — read it from `git branch --show-current`.
- Never assume remote names mean what they sound like — inspect `git remote -v` and `git branch -vv`; determine the fork and canonical upstream from their URLs.
- Preserve pre-existing working-tree changes during synchronization: compare them with the target ref before staging, and never discard them to make a merge succeed.

## Multi-remote fork synchronization

Use this workflow when a working branch belongs to a server fork and the canonical project has a `beta` branch:

1. Read `git remote -v`, `git branch -vv`, and `git status`. Identify the fork remote and canonical upstream from the actual URLs; do not infer them from names such as `origin` or `upstream`.
2. Fetch canonical `beta` into a temporary local ref (`git fetch <canonical> beta:refs/sync/canonical-beta`) and verify its SHA with `git ls-remote`. Keep this fetch as a separate ref until the fork update is verified.
3. Push the verified temporary ref to the configured fork's `beta` using an explicit refspec. Do not change remote configuration or hardcode a server-specific branch name.
4. Before updating the current branch, fetch its remote ref and compare both merge bases and left/right counts. If the remote current branch has commits, merge it first; never force-push a divergent branch.
5. Preflight the update with `git merge-tree --write-tree --messages HEAD <target>`. Resolve conflicts from the base, current, and incoming versions semantically, then stage only after checking markers and syntax.
6. Merge the synchronized fork `beta` into the current branch, run the affected tests, push `HEAD:<current-branch>` explicitly, and fetch again to verify local, tracking, and remote refs.

**Pitfall:** branch tracking can point to a different branch, such as `branch.<name>.merge=refs/heads/beta`; `git status` may therefore report the current branch against `beta` even when a same-named remote branch exists. Use explicit refspecs and inspect `git branch -vv`.

**Conflict gate:** a clean syntax check is insufficient after a merge. Check variable names and test semantics against both sides, run the affected test files, and verify `git diff --check` plus a clean status before committing.

See `references/remote-branch-sync.md` for the reusable command sequence and verification checklist.

## Pitfalls

### Nested `.git` directories when copying content

When `cp -r` (or similar) a directory that contains its own `.git` into another repo,
`git add` detects the nested `.git` and stages only a submodule reference (mode 160000),
not the actual files. Clones of the outer repo will not contain the copied content.

**Fix — remove nested `.git` before staging:**

```bash
cp -r /source/dir target/inside/repo
rm -rf target/inside/repo/.git
git add target/inside/repo/
```

If already staged as submodule:

```bash
git rm -r --cached target/inside/repo/
rm -rf target/inside/repo/.git
git add target/inside/repo/
git commit -m "Add dir contents (fix nested repo)"
```

### Missing git identity on fresh clones

New clones may lack both global and per-repo `user.name`/`user.email`.
Commits fail with `empty ident name`.

**Fix — set per-repo config before first commit:**

```bash
git config user.email "user@users.noreply.github.com"
git config user.name "username"
```

Detect from `gh auth status` or set manually.

### Parallel subagent implementations on one branch

When implementing multiple independent issues via `delegate_task` subagents:

1. **Do not commit per-subagent.** Let each subagent modify files and run its own targeted tests, but instruct it NOT to commit or push.
2. **Run a combined verification** after all subagents finish: `composer phpstan`, `composer pint`, and the union of affected test files — before any commit. Subagents may have introduced formatting drift in each other's files (e.g. Pint auto-fixing a file another agent touched), and only the combined pass proves the branch is coherent.
3. **Single commit per batch.** `git add -A && git commit` once, with a message listing all issues addressed.
4. **Update (do not recreate) the PR** with `gh pr edit` when the branch already has an open PR.

## Verification

- `git status` shows no unexpected submodule entries.
- `git diff --cached --stat` shows actual file additions, not just mode changes.
- Commit and push succeed without warnings about embedded repos.
