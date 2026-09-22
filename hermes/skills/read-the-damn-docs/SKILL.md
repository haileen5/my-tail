---
name: read-the-damn-docs
description: "Read current official docs before assuming from memory."
---

# Read The Damn Docs

Do not guess where authoritative docs can answer the question. The most common right move is to web-search for the current official docs, open the relevant pages, and read them before coding.

## Docs-First Triggers

Read docs before proceeding when any of these are true:

- The user asks for "latest", "current", "official", "supported", "best practice", "recommended", "today", "now", or "look it up".
- The needed docs are not already in the repo or supplied by the user. Search the web for the official docs rather than hoping model memory is current.
- The task adds, upgrades, configures, or imports a package, SDK, framework, plugin, CLI, model, cloud resource, or provider integration.
- The API is fast-moving or version-sensitive: AI SDKs, OpenAI/Anthropic/Google APIs, Next.js, React, Tailwind, Vite, Nitro, Drizzle, Prisma, Stripe, GitHub, Slack, Notion, browser APIs, deployment platforms, auth libraries, and similar.
- The implementation depends on auth, OAuth scopes, permissions, secrets, webhooks, billing, payments, PII, encryption, data retention, migrations, retries, rate limits, quotas, caching, deploys, or compliance.
- An error mentions deprecation, unknown options, missing exports, invalid config, unsupported fields, changed defaults, or version mismatch.
- A repo has local docs, ADRs, generated schemas, OpenAPI specs, route/action registries, design-system docs, or package-level READMEs that could define the contract.
- The choice is expensive to reverse: public wire formats, database schema, migration strategy, persistent IDs, event names, customer-visible behavior, or external automation contracts.
- You catch yourself about to write "usually", "probably", "I think", "from memory", or code copied from model memory for an external API.

## Required Workflow

1. Identify the exact surface: package name, installed version, target version, provider endpoint, CLI command, config file, local helper, schema, or product feature.
2. Search the web for the current official docs unless the relevant docs are already local or the user supplied a URL.
3. Open and read the docs closest to that surface. Prefer local docs first for internal code, then official upstream docs.
4. Extract the few facts needed for the task: option names, imports, lifecycle rules, default behavior, breaking changes, limits, permissions, and examples for the current major version.
5. Implement or answer using those facts. If the docs conflict with existing code, inspect the local code path and call out the discrepancy.
6. Verify with the smallest useful check: typecheck, tests, build, CLI dry run, API schema validation, or a local reproduction.
7. In the final answer, name the docs or local files consulted.

## When A Quick Local Read Is Enough

Do not browse the web for every tiny edit. A docs pass can be local and brief when the answer is already in the repo. But if the task depends on an external tool, package, provider, or current product behavior, web search is usually the right first step.