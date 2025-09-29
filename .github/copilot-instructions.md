# Copilot / AI agent instructions for MCP_Demo

Summary
- Repo snapshot: very small demo repository named `MCP_Demo` containing only `README.md` and `.gitattributes` at the time of inspection.
- No build system, package manifest, source code, tests, or CI configuration were found.

Primary goal for agents
- Be conservative: do not assume language/runtime. Ask the user when the project needs a specific stack (Node/Python/Go/etc.).
- When asked to implement features, first propose a minimal scaffolding (package manifest, basic linter/test config) before adding substantial code.

First actions (automated agent checklist)
1. Run a repo scan to confirm current files: list top-level and hidden files (look for `package.json`, `pyproject.toml`, `go.mod`, `Dockerfile`, `.github/workflows`).
2. Open `README.md` (root) and `.gitattributes` to capture stated intent. This repo currently only has `README.md` with title `MCP_Demo`.
3. If no language or build is present, ask the user which language/runtime they prefer. Offer sensible starter scaffolds (Node+npm, Python+venv/pyproject, Go modules).

What to change and how to propose it
- Keep changes small and modular. Create one feature or scaffold per branch and open a PR with a short description.
- When adding scaffolding, include a minimal README update that documents how to build/run/test the added scaffold.
- Example: if adding a Node scaffold, include `package.json` with scripts: `test`, `lint`, `start` and a one-line `npm install`/`npm test` run in the PR description.

Patterns & conventions (discoverable)
- There are no project-specific code conventions discovered. Use common idiomatic patterns for the chosen language.
- Preserve existing files (`README.md`, `.gitattributes`), and avoid altering repository-level git attributes unless explicitly requested.

Integration points & checks
- Before adding external dependencies, search the repo for existing manifests. If none found, list proposed dependencies in the PR description and explain why.
- Do not call external services or include credentials/secrets in commits. If the task requires external APIs or credentials, request them and document expected environment variables.

Developer workflows (what to document in PRs)
- Build & test commands you added (copyable). Example: ``npm install && npm test`` or ``python -m venv .venv && .venv/bin/pip install -r requirements.txt && pytest``.
- How to run a quick smoke test and expected success criteria.
- Any lint/typecheck commands and their expected pass/fail exit codes.

When to stop and ask
- If the repository lacks a clear purpose or language, stop and ask the user to confirm the intended stack.
- If a requested feature requires sensitive credentials, external accounts, or organizational approvals, stop and ask.

Key files to inspect when you start work
- `README.md` — project intent (currently empty except title)
- `.gitattributes` — git line-ending behavior
- `.github/` — where to add workflows, issue templates, or this file

If you were asked to add features now
- Propose a short plan as a comment: (1) chosen language/runtime, (2) minimal files to add, (3) tests to include, (4) one smoke test command.

Notes for reviewers
- PRs from agents should be limited in scope. Each PR must include a short checklist: files added, commands to run, and quick verification steps.

If anything in this file is unclear or you want the agent to bootstrap a specific stack (Node/Python/Go), tell me which stack and I'll implement a minimal scaffold with tests and documentation.
