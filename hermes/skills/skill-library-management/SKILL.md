---
name: skill-library-management
description: "Acquire, verify, and stage third-party skills."
version: 1.0.0
author: Sydney
license: MIT
metadata:
  hermes:
    tags: [skills, install, verify, library, provenance]
    category: software-development
---

# Skill Library Management

Covers the class of task where someone hands you a skill — a URL, a repo path, a
name — and asks you to add it, use it, or hold it ready. The work is mostly
*verification and boundaries*, not authoring: a skill that is already present
is usually the common case, and rewriting it is a regression.

For authoring a NEW skill from scratch, see `hermes-agent-skill-authoring` (that
skill covers in-repo authoring standards; this one covers acquisition).

## When to Use

- "add this skill <URL>", "install this skill", "pull in <owner>/<repo> skill"
- "use skill X" where X may or may not be installed
- "load X but don't run it yet" / "have it ready"
- A quarterly or ad-hoc sweep reconciling the local library against upstream

Don't use for: writing a skill body (authoring), or debugging the agent runtime
itself (use `hermes-agent`).

## Procedure

1. **Resolve the name before writing anything.** The requested URL often points
   at a repo (`.../blob/main/skills/<name>/SKILL.md`) whose directory name is
   the skill's real name — the `name:` in frontmatter, not the URL's last path
   segment. Read the file; do not infer the name from the URL.

2. **Check what already exists.** `skills_list` and `search_files` over the
   skills root. This is the step that decides everything downstream.

3. **If the skill is present, diff it against upstream — do NOT reinstall.**
   Fetch the raw file (`raw.githubusercontent.com` for a `github.com/.../blob/`
   URL; `web_extract` works too) and compare:

   ```bash
   diff <(curl -sL <raw-url>) <installed-path>/SKILL.md && echo IDENTICAL
   ```

   Report "already installed, byte-identical to upstream" and stop. A blind
   reinstall over a locally adapted skill silently destroys local edits.

4. **Only install when genuinely absent.** Prefer the platform's own installer
   over hand-copying a `SKILL.md` into the skills root — the installer sets
   ownership markers, and hand-copying produces a skill that later looks
   curator-managed when it is not.

5. **Verify by loading, not by existence.** `skill_view(name)` must return
   content. A directory with a `SKILL.md` that fails to parse (bad frontmatter,
   missing `name`/`description`) is not installed, however present it looks on
   disk.

6. **When asked to stage without executing** (load it, don't run the workflow):
   `skill_view` it and say so explicitly, then take no further action from that
   skill's instructions. Distinguish "the skill is in context" from "the skill's
   workflow ran" in the final report — the user is gating on that difference.

7. **Confirm ownership before any later edit.** Record which skills are
   user-owned, hub-installed, bundled, or externally-sourced. Never rewrite
   them to "fix" something; report the issue and recommend the adopt path
   instead.

## Ownership Boundaries

The single most expensive mistake here is editing a skill you do not own.

- **Do not edit:** bundled skills shipped with the agent; hub-installed skills;
  anything in an external skills directory; pinned skills; user-owned skills —
  including ones the user hand-wrote, installed by URL, or asked a foreground
  agent to create.
- **Do edit:** skills the curator manages.
- Being *loaded*, *consulted*, or *relevant* never confers ownership. If the
  only skills needing an update are protected, say so and stop — do not attempt
  the write.

## Pitfalls

### Reinstalling over an already-present skill

The request says "add", which reads as "it is missing", and it usually is not.
Reinstalling is destructive when the local copy has been adapted. Diff first —
that single command turns a guess into a fact and costs one fetch.

### Inferring the skill name from the URL

Repo directory names, URL segments, and frontmatter `name:` disagree often
enough to matter. A skill installed under the wrong directory name never
matches `skill_view`, so it silently fails to load every later session. Read
frontmatter for the authoritative name.

### Verifying installation by file presence

A `SKILL.md` on disk proves nothing if the loader rejects it. The check is one
`skill_view` returning real content — the same "configured is not working"
discipline that applies to MCP servers and CLIs.

### Treating a staging request as an execution request

"Use skill X but don't run it yet" means load, report, and stop. Executing the
workflow anyway spends the thing the user was deliberately holding back.

### Assuming you may fix a skill that behaved wrong

A third-party skill that is subtly off still belongs to its owner. Patch
attempt is refused; the fix is to surface the discrepancy and let the user
adopt or pin deliberately.

## Verification Checklist

- [ ] Skill name resolved from frontmatter, not guessed from the URL
- [ ] Existing installation checked before any write
- [ ] Present-and-diverging → reported, NOT overwritten
- [ ] Absent → installed via the platform installer, not hand-copied
- [ ] `skill_view` returns real content
- [ ] "Load but don't run" honored: loaded, reported, workflow not executed
- [ ] Ownership known before any edit; protected skills untouched
