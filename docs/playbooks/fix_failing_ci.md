Playbook: Diagnose and Fix Failing CI

## Overview
Take a pull request (or branch) with failing CI, find the real root cause of each failing check, fix it properly, and get the pipeline green — while clearly separating failures caused by the PR from failures that already exist on the base branch.

## What's Needed From User
- PR link or branch name with failing checks
- Whether fixes should land on the PR branch or a new branch
- Any known-flaky tests or jobs that can be re-run rather than fixed

## Procedure
1. List the failing checks on the PR and pull the logs for each failing job; do not guess from job names.
2. For each failure, extract the first real error (not the downstream cascade) and classify it: product bug, test bug, environment/config issue, or pre-existing failure.
3. Determine whether the failure exists on the base branch — check the base branch's own CI history or reproduce it locally on the base commit. Never call a failure "pre-existing" or "flaky" without this evidence.
4. Reproduce each PR-caused failure locally with the same command CI runs, so the fix can be verified without waiting on the pipeline.
5. Fix the root cause: correct the code when the product is wrong, correct the test only when the test itself is genuinely wrong, and fix config/dependency issues at their source.
6. Re-run the failing commands locally until clean, then run the full local verification set (tests, lint, typecheck, build) to make sure the fix broke nothing else.
7. Push the fix and watch CI through to completion, iterating on any new failures.
8. If CI still fails after three focused attempts, stop and report to the user with the logs, the root-cause hypothesis, and what was tried.
9. Report back: each failing check, its root cause, the fix, and the final CI status; list separately any pre-existing failures left untouched and why.

## Specifications
- Every failing check is either fixed or explicitly reported as pre-existing with evidence
- Fixes address root causes, not symptoms; no skipped, deleted, or weakened assertions
- No changes to CI configuration that reduce coverage or bypass checks
- Deliverable: green CI plus a short root-cause summary per originally-failing check
- Validation: all required checks pass on the PR head commit

## Advice and Pointers
- Read the earliest error in the log; later errors are usually consequences.
- Dependency and lockfile failures are often environment drift — check whether the lockfile and the installed versions agree before touching source.
- If a test is genuinely flaky, say so with evidence (e.g. it passes on re-run with no code change) rather than deleting it.

## Forbidden Actions
- Do not use `--no-verify`, skip hooks, or mark tests as skipped/xfail to get green
- Do not relax lint/type rules, coverage thresholds, or security settings to bypass a failure
- Do not amend or force-push over other people's commits
- Do not claim a failure is unrelated without checking the base branch
