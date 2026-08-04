# Lifting non-power users: a Devin enablement playbook

Goal: close the gap between power users (many merged PRs per week, low ACU/PR, few course corrections) and everyone else, across teams that each use Devin for their own use cases.

The core insight: the gap is almost never "the user needs to try harder." It is nearly always one of six mechanical failure modes, each of which has a **detectable signal** and a **one-time fix that keeps paying off**. Fix the environment and the reusable assets once, and mediocre prompts start succeeding.

---

## 1. The six failure modes, how to detect them, and what to do

| # | Failure mode | Detection signal (Session Insights / session list) | Fix |
|---|---|---|---|
| 1 | **Broken/absent environment setup** — Devin spends the session installing deps, guessing build commands, hitting missing credentials | High ACU with **few user messages**; L/XL session size for a small task; action items tagged `machine_setup` / `repo_config` | Repo **blueprint** (declarative env config) + snapshot so every session starts with deps installed, app runnable, tests passing. This is the single highest-leverage fix. |
| 2 | **Vague, decision-free prompts** — "improve performance", "make it look better" | **High user-message count** (lots of course correction); Insights' *Improved Prompt* differs radically from the original | Prompt template + the "Ask Devin first" habit (below). Have users start sessions **from Ask Devin**, which auto-generates a high-context prompt. |
| 3 | **Wrong task selection** — architecture decisions, sprawling multi-service features, aesthetics with no spec | Session ends with a PR nobody merges; user abandons mid-session; repeated "not what I wanted" | Publish a team-specific **green/yellow/red task list** (§3). Devin's sweet spot: high-volume repetitive slices, junior-to-mid complexity, isolated, objectively verifiable. |
| 4 | **No verification loop** — no tests, no lint, no CI, no "how do I know it worked" | PRs bounce in review; Devin claims success, reviewer disagrees | Require explicit success criteria in every prompt ("CI green", "`npm test` passes", "screenshot at 375px"). Turn on **Devin Review + Auto-Fix** so PRs self-iterate to merge-ready. |
| 5 | **No reusable context** — every user re-types the same conventions; tribal knowledge lives in heads | Same corrections appear across many sessions and users | **Knowledge notes** (persistent conventions, auto-recalled, pinnable per repo) + **Playbooks** (step-by-step procedures for recurring task types). Zero playbooks/notes in an org is a red flag. |
| 6 | **Workflow not where the work is** — Devin is a separate website they forget to open | Low session count per active user; usage spikes only after trainings | Wire Devin into existing surfaces: Slack/Teams tagging, Linear/Jira ticket handoff, CLI for local work, scheduled sessions for recurring chores. |

> Rule of thumb for reading a session: **high ACU + low messages = environment or ambiguity problem. Low ACU + high messages = prompt problem.**

---

## 2. Org-level fixes (do these once; they lift everyone)

Ordered by leverage per hour invested.

1. **Blueprints for the top ~10 repos.** Deps installed, services runnable, test/lint commands defined, secrets provisioned. Non-power users can't debug a broken env, so they just give up — power users silently paper over it.
2. **Seed Knowledge notes per repo.** Coding standards, how to run tests, deploy flow, common footguns, internal tool usage. Pin repo-specific notes to the repo, keep global notes short. Review Insights' "note usage" to prune notes that mislead.
3. **Ship 5–10 Playbooks for the org's actual recurring tasks.** Best candidates: fix failing CI, add unit tests to module X, dependency bumps, Sentry triage, ticket-to-PR for a specific service, migration slice. A playbook turns a weak prompt into a strong one automatically.
4. **Turn on Devin Review with Auto-Fix.** It closes the loop without the user being competent at reviewing agent output — the biggest single differentiator between power and non-power users.
5. **Connect the integrations that matter**: Slack/Teams (start sessions from the thread where the bug is discussed), Linear/Jira, and MCP servers for Sentry/Datadog/Figma/DBs. Each connected system removes a class of "Devin lacked context" failure.
6. **Generate DeepWiki for every active repo, and teach Ask Devin as the entry point.** DeepWiki auto-indexes a repo into a wiki with architecture diagrams, source links, and summaries, and Ask Devin uses it to answer grounded, cited questions about the code. This directly fixes the most common prompting failure: users who cannot name the right files or the pattern to imitate, because they do not know the codebase. Wikis are generated automatically when repos are connected — check that the repos your weak users work in actually have one.
7. **Scheduled/automated sessions** for recurring chores so teams get value without anyone writing a prompt at all.

---

## 3. Give each team a task menu (not generic advice)

Generic "write better prompts" training does not stick. A one-page, team-specific list does:

- **Green (just delegate):** unit tests, dependency bumps, lint/type-error cleanup, ticket-sized bugs with a repro, repetitive migration slices, docs, codebase Q&A, boilerplate integrations, internal tools/prototypes.
- **Yellow (delegate with a spec/reference file):** new endpoints or components following an existing pattern, refactors with tests as a safety net, UI work with a Figma/design spec, cross-file feature work.
- **Red (scope with a human first, or use DeepWiki + Ask Devin to plan):** architecture choices, ambiguous product decisions, aesthetic-only work with no reference, anything with no way to verify success, sprawling multi-service changes.

Have each team's power user fill this in for their own domain — it takes 30 minutes and is far more persuasive than corporate docs.

---

## 4. The habits that separate power users (teach exactly these five)

1. **Scope in Ask Devin first** (backed by the repo's DeepWiki), then start the session from that conversation — the prompt is auto-generated with real codebase context, so the user never has to know the file layout by heart.
2. **Be opinionated.** State the file, the pattern to follow, the library, the approach. Make the judgment calls instead of leaving them to Devin.
3. **State the finish line.** "Done = CI green + new tests for X + screenshot of the settings page."
4. **Keep sessions XS/S/M.** Split large work into parallel sessions rather than one giant one.
5. **Run a post-session review.** Generate Insights analysis, take the *Improved Prompt*, and promote anything reusable into a Knowledge note or Playbook. This is the compounding habit; almost no non-power user does it unprompted.

**Copy-paste prompt skeleton to hand out:**

```
Goal: <what outcome, in one sentence>
Repo//files: <repo, key files, the pattern to imitate, e.g. "follow authTemplate.rs">
Approach: <the decision you've already made for Devin>
Constraints: <libraries, perf/security limits, what not to touch>
Done when: <tests pass / CI green / screenshot at 375px / endpoint returns 200 with fields X,Y>
Report back: <what to tell me, and when to stop and ask>
```

---

## 5. A 30/60/90 rollout

**Days 1–30 — remove the blockers**
- Pull org session data (Insights API: sessions + per-session analysis) and rank issues by `action_item.type` (`machine_setup`, `repo_config`, `knowledge`, `prompt_improvement`).
- Fix blueprints for the repos generating the most `machine_setup`/`repo_config` items.
- Enable Devin Review + Auto-Fix; connect Slack/Teams and the ticket tracker.
- Identify each team's power user; name them "Devin champions."

**Days 31–60 — build reusable assets**
- Each champion ships 2–3 playbooks + a repo knowledge pack for their team's use case.
- Publish the per-team green/yellow/red task menu and the prompt skeleton.
- Run 45-minute, team-specific working sessions: everyone brings a real ticket and delegates it live. No slideware.
- Pair each low-usage user with a champion for one session (watching a power user delegate is the fastest teaching mechanism).

**Days 61–90 — make it a habit and measure**
- Weekly champion sync: review the 3 worst sessions of the week, convert learnings into knowledge/playbooks/blueprint changes.
- Add scheduled sessions for recurring chores per team.
- Report on the metrics below; retire assets nobody uses.

---

## 6. Metrics that actually track effectiveness

Per user and per team, tracked monthly:

- **Merged PRs per active user** (the outcome metric — not session count).
- **ACU per merged PR** (efficiency; falling = environment/prompts improving).
- **Median user messages per session** (falling = prompts improving).
- **Session size distribution** (share of XS/S/M vs L/XL — more small sessions is healthier).
- **Session-to-PR rate** and **PR merge rate** (abandonment = task-selection problem).
- **Asset leverage:** % of sessions using a playbook or hitting a knowledge note.
- **Surface mix:** share of sessions started from Slack/tickets/CLI vs. cold in the webapp (higher = embedded in workflow).

Segment the bottom quartile by these and the intervention picks itself: high ACU/low messages → env; high messages → prompting; low merge rate → task selection; low session count → workflow integration.

---

## 7. What I'd do first (highest value per hour)

1. Blueprints for the top repos.
2. Devin Review + Auto-Fix on, and DeepWiki generated for every active repo.
3. Three playbooks per team, written by that team's power user.
4. The one-page task menu + prompt skeleton.
5. Weekly "worst session review" ritual that feeds 1–4.

---

### Companion playbook drafts

`docs/playbooks/` holds the starter playbooks referenced above, ready to paste into /settings/playbooks:

- `ticket_to_pr.md` — the bread-and-butter delegation procedure (`!ticket_to_pr`)
- `fix_failing_ci.md` — root-cause CI triage without weakening tests (`!fix_ci`)
- `session_postmortem.md` — converting a bad session into permanent assets (`!session_postmortem`)

### Sources
- https://docs.devin.ai/essential-guidelines/instructing-devin-effectively
- https://docs.devin.ai/essential-guidelines/when-to-use-devin
- https://docs.devin.ai/product-guides/session-insights
- https://docs.devin.ai/product-guides/creating-playbooks and /using-playbooks
- https://docs.devin.ai/product-guides/knowledge
- https://docs.devin.ai/work-with-devin/devin-review
- https://docs.devin.ai/work-with-devin/ask-devin
- https://docs.devin.ai/work-with-devin/deepwiki
- https://docs.devin.ai/use-cases/best-practices
