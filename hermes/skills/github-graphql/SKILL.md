---
name: github-graphql
description: Use when gh has no command for GitHub GraphQL-only features.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, graphql, discussions, gh, api]
    category: software-development
    related_skills: [github]
---

# GitHub beyond `gh` porcelain (GraphQL)

Discussions and some other surfaces are GraphQL-only: no `gh` subcommand, no
REST route. The route is always `gh api graphql` with the token already in
`GH_TOKEN` — no curl, no extra auth setup.

## When to Use

- Creating, listing, or reading GitHub **Discussions** and their categories.
- Any GitHub data/action where `gh <subcommand>` and the REST API both come up
  empty (project fields, some org-level nodes) — find the node in the GraphQL
  schema, then follow the procedure below.
- Not for issues, PRs, releases, checks, or repo admin: the `github` skill's
  `gh` porcelain covers those and is faster.

## Procedure

1. **Resolve the target repo explicitly** — pass `owner/name` in the query
   (or `-R owner/repo` on any porcelain call). Never infer it from the current
   directory's remotes: the working copy is often a fork, and forks ship with
   issues/discussions disabled, which surfaces as
   `the '<fork>' repository has disabled issues`.
2. **Preflight auth:** `gh auth status` — confirm the token's scopes include
   `write:discussion` before attempting a mutation (reads work with plain
   `repo`/public access).
3. **Look up the node IDs the mutation needs:**
   ```bash
   gh api graphql -f query='query{repository(owner:"OWNER",name:"REPO"){id discussionCategories(first:20){nodes{id name slug}}}}'
   ```
   Returns the repository `ID` and every discussion category (`Ideas`,
   `Q&A`, …) with its `DIC_…` id — `createDiscussion` needs both.
4. **List what already exists** before drafting: existing posts reveal the
   working category names, the language/tone the repo uses, and duplicates of
   your idea.
   ```bash
   gh api graphql -f query='query{repository(owner:"O",name:"R"){discussions(first:10,orderBy:{field:CREATED_AT,direction:DESC}){nodes{title url category{name}}}}}'
   ```
5. **Draft → show → send, unless the user pre-authorized the batch.** Present
   title + body before the mutation; approval of the idea is not approval of
   the send. When the user grants blanket approval ("post your own take on
   each of them, no confirmation needed"), draft, send, and verify the whole
   batch in one pass instead of re-asking per item.
   Ground every factual claim in the draft against the current code first
   (file + line, read in this session) — a public comment is permanent and
   will be quoted back; a wrong file or line costs more than the post is worth.
6. **Create:**
   ```bash
   gh api graphql -f query='mutation($repo:ID!,$cat:ID!,$title:String!,$body:String!){createDiscussion(input:{repositoryId:$repo,categoryID:$cat,title:$title,body:$body}){discussion{url}}}' \
     -f repo="$REPO_ID" -f cat="$CATEGORY_ID" -f title="$TITLE" -f body="$BODY"
   ```
   Verify by printing the returned `discussion.url` — never report success
   from a zero exit code alone.

7. **Commenting on an existing discussion** is `addDiscussionComment` with the
   discussion's `D_…` id (fetched in step 3-style reads, never derived from
   the number). For any body longer than a phrase, put query + variables in
   one JSON file — a multi-line Markdown body inlined into a shell command
   only survives if every quoting layer agrees, and usually doesn't:
   ```json
   {"query": "mutation($id: ID!, $body: String!){addDiscussionComment(input:{discussionId:$id, body:$body}){comment{url}}}",
    "variables": {"id": "D_…", "body": "…markdown…"}}
   ```
   ```bash
   gh api graphql --input input.json
   ```
   Verify per target with a fresh read, not the mutation response:
   `discussions{nodes{number comments(last:1){totalCount nodes{url author{login}}}}}`
   — for a batch, every count must have moved and every URL must resolve.

## Pitfalls

- **Pass the query as a raw string, never JSON-wrapped.**
  `-f query='{"query":"..."}'` dies with `invalid key: "{..."` — `gh` parses
  `-f` as `key=value` and rejects a key that isn't a bare identifier. The
  query document itself IS the value.
- **Never inline user-authored text into the query document.** Persian titles,
  Markdown, quotes and newlines break the query string — pass payload as
  separate `-f title="$TITLE" -f body="$BODY"` variables so nothing is
  re-parsed by the shell.
- **`-f`, not `-F`, for `ID`/`String!` arguments.** `-F` coerces the value to
  number/bool/null, which type-errors against `ID!` and `String!`; `-f` passes
  it as a string.
- Building the command from Python (`execute_code`): wrap the query with
  `shlex.quote` (`shell_quote`) — raw f-string interpolation of a query
  containing `"` fails at the shell before `gh` ever runs.
- **`body` on Discussion/comment nodes is a String scalar.**
  `body(first:200){text}` dies with `Selections can't be made on scalars`;
  select `body` bare and truncate in Python. Only paginate fields the schema
  declares as connections (`nodes`, `pageInfo`).
- **GraphQL errors arrive on stdout with exit code 1, as JSON.** Parse stdout
  and check the `errors` key explicitly — both an exit code of 0 with a raised
  `errors` array and a non-JSON error blob that breaks `json.loads` are
  possible, so neither the exit code nor a blind load is a validity check.