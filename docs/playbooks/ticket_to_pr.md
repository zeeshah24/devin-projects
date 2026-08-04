Playbook: Ticket to Review-Ready PR

## Overview
Take a well-scoped ticket or bug report and deliver a review-ready pull request: reproduce or confirm the problem, implement the change following existing patterns in the repo, verify it with the repo's own tests and linters, and open a PR with a description a reviewer can act on without reading the whole diff.

## What's Needed From User
- Ticket link or description (Linear/Jira/GitHub issue, or plain text) with the expected behavior
- Repository, and ideally the files or module involved
- A reference file or existing pattern to imitate (e.g. "follow `src/api/authHandler.ts`")
- Definition of done (e.g. "CI green + a regression test", "endpoint returns 200 with fields X, Y")
- Any constraints: libraries to use or avoid, code that must not be touched, perf/security requirements

## Procedure
1. Restate the task in one or two sentences: the change, the affected files, and how success will be verified. If the ticket leaves a design decision open, ask the user before writing code rather than guessing.
2. Locate the relevant code and read the reference pattern the user pointed to, plus its tests, so the change matches existing conventions.
3. Identify the repo's verification commands (test, lint, typecheck, build) from README/CONTRIBUTING, package manifests, or CI config, and confirm they run before making changes.
4. For a bug: reproduce it first with a failing test or a concrete repro command, and report the repro to the user. For a feature: outline the intended change in a short message before implementing.
5. Implement the change with minimal, focused edits — only the files the task requires, matching surrounding style, no unrelated refactors.
6. Add or update tests covering the new behavior (for bugs, the test must fail before the fix and pass after).
7. Run the full verification set (tests, lint, typecheck, build) and fix everything until clean.
8. Open the PR against the correct base branch with a description covering what changed, why, and how it was verified; link the ticket.
9. Watch CI and fix failures. Never disable, skip, or weaken a test to make CI pass — if a failure looks pre-existing, verify it on the base branch before saying so.
10. Report back with the PR link, what was verified, and anything intentionally left out of scope.

## Specifications
- Scope stays inside the ticket: no drive-by refactors, dependency bumps, or formatting sweeps
- New behavior is covered by tests; for bug fixes the test demonstrably fails without the fix
- Repo test, lint, typecheck, and build commands all pass locally and in CI
- Deliverable: a PR link plus a one-paragraph summary of the change and the verification performed
- Validation: CI is green on the PR and the definition of done stated by the user is met point by point

## Advice and Pointers
- Ambiguity is the main failure cause. One clarifying question up front beats a wrong 200-line diff.
- Prefer the pattern already used in the repo over the "better" pattern you would choose from scratch.
- If the task turns out to be much larger than the ticket implies, stop and propose a split into smaller PRs.
- Check whether a library is already a dependency before introducing it.

## Forbidden Actions
- Do not modify unrelated tests, or change tests so failing code passes
- Do not commit secrets, `.env` files, or generated artifacts
- Do not push to `main`/`master` or force-push shared branches
- Do not silently expand scope beyond the ticket
