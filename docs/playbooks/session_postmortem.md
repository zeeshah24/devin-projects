Playbook: Session Post-Mortem and Reusable-Asset Extraction

## Overview
Turn a disappointing or expensive Devin session into permanent improvements. Diagnose why the session underperformed, classify the root cause (environment, prompt, task selection, missing context, or product limitation), and convert the learnings into a better prompt plus concrete knowledge notes, playbook changes, or environment fixes. This is the habit that separates power users from everyone else.

## What's Needed From User
- One or more session links to review
- What the user expected versus what they got
- Whether they want proposals only, or the knowledge/playbook/blueprint changes prepared for approval

## Procedure
1. Read the session: the original prompt, the work performed, where it went off track, and how many user course-corrections were needed.
2. Record the headline numbers — ACUs consumed, user message count, session size, PR outcome — and compare against the user's expectation.
3. Classify the root cause using the dominant signal:
   - High ACU with few user messages → environment setup or ambiguous requirements causing trial and error
   - Many user messages → the initial prompt lacked context, constraints, or a definition of done
   - Abandoned or unmerged output → wrong task for delegation, or no objective way to verify success
   - Repeated rediscovery of conventions → missing knowledge notes
4. Quote the specific moments in the session that support the classification, so the diagnosis is evidence-based rather than a guess.
5. Rewrite the original prompt into an improved version containing: goal, repo and reference files, the approach decision, constraints, definition of done, and what to report back.
6. Extract durable assets from the learnings: knowledge notes for conventions that should apply to every future session, playbook updates for recurring procedures, and environment/blueprint fixes for anything the machine was missing.
7. Check whether the fix belongs at the org level (affects everyone) or the repo level (affects one codebase), and scope it accordingly.
8. Prepare the proposed knowledge notes, playbook updates, or blueprint changes for the user's approval, and note anything that requires a human decision (missing credentials, access, product gaps).
9. Report back with: root cause, the improved prompt, the assets proposed, and the one change most likely to prevent a repeat.

## Specifications
- Root cause is supported by specific evidence from the session, not speculation
- The improved prompt is self-contained and could be pasted into a new session as-is
- At least one durable asset (knowledge note, playbook change, or environment fix) is proposed when the root cause is recurring
- Deliverable: a short written post-mortem plus the proposed assets
- Validation: re-run the original task with the improved prompt and confirm fewer course corrections and a usable result

## Advice and Pointers
- Environment problems masquerade as model failures. Check setup, dependencies, and credentials before blaming the prompt.
- One-off task details do not belong in knowledge notes; only capture what generalizes across sessions.
- If the same root cause appears in several sessions, fix it once at the org level rather than coaching each user individually.

## Forbidden Actions
- Do not write secrets, tokens, or credentials into knowledge notes or playbooks
- Do not create duplicate knowledge notes without checking existing ones first
- Do not conclude "the model just failed" without ruling out environment, prompt, and task-fit causes
