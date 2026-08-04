# Measuring who uses Devin well — and diagnosing who needs help

A plan for collecting per-user Devin usage data, classifying users by effectiveness, and mapping each lagging signal to a specific intervention. The output is not a leaderboard: it is a work queue of fixes, most of which are the organization's responsibility rather than the user's.

Companion to [devin-enablement-playbook.md](devin-enablement-playbook.md), which describes the interventions this plan selects between.

---

## 1. Principles before metrics

1. **Measure outcomes, not activity.** Session count and ACUs spent are inputs. Merged PRs and accepted work are outputs. A user running 40 sessions and merging nothing is the problem case, not the star.
2. **Never use this for performance management.** The moment it becomes a ranking of engineers, users game it (or stop using Devin). Frame it as "where is the tooling failing people."
3. **Compare within cohorts.** A platform team's tasks are not a frontend team's tasks. Segment by team and by repo before comparing users.
4. **Prefer relative thresholds.** Use the org's own quartiles rather than invented absolute cutoffs — they hold as models and the product change.
5. **Every red signal must resolve to an owner and an action.** A metric that does not select an intervention should not be on the dashboard.

---

## 2. Data sources

| Source | What it gives | How to get it |
| --- | --- | --- |
| Session insights (list) | Per session: `user_id`, `acus_consumed`, `num_user_messages`, `num_devin_messages`, `session_size` (xs–xl), `status`, `status_detail`, `pull_requests[].pr_state`, `origin`, `playbook_id`, `category`/`subcategory`, `devin_mode`, `tags`, timestamps | `GET /v3/organizations/{org_id}/sessions/insights` (date and user filters supported; paginate) |
| Session insights (single) | The AI analysis: `analysis.issues[]`, `analysis.action_items[].type` (`machine_setup`, `repo_config`, `knowledge`, `prompt_improvement`, `external`, `other`), `analysis.suggested_prompt`, `analysis.note_usage.{good,bad}_usages`, `analysis.timeline` | `GET /v3/organizations/{org_id}/sessions/{devin_id}/insights` — analysis is generated on demand, so trigger it for the sessions you sample |
| Org analytics dashboards | Active users, engagement trends, consumption | Settings → Analytics |
| Git provider | Merge rate, review turnaround, revert rate, lines changed per PR | GitHub/GitLab API on the PR URLs returned above |
| DeepWiki coverage | Which active repos have a generated wiki backing Ask Devin's answers | Wiki section of the app; treat a missing wiki on a frequently-used repo as a defect |
| Knowledge & playbook inventory | Which assets exist, which are actually used (`playbook_id` on sessions, `note_usage` in analysis) | Playbooks and Knowledge settings + the fields above |

`analysis.action_items[].type` is the most valuable field in the whole dataset: it is Devin's own classification of what went wrong, and it maps almost one-to-one onto the interventions in §6.

---

## 3. Collection pipeline

Run this as a **scheduled Devin session** (weekly, Monday morning) rather than building bespoke infrastructure:

1. Pull all sessions from the last 7 days via the org insights list endpoint, paginating to completion.
2. For sessions that are L/XL, ended in `error`/`suspended`, or produced no PR, request the per-session insights so the AI analysis is generated (analysis is the expensive part — sample rather than analysing everything).
3. Append the flattened rows to a CSV or warehouse table keyed by `session_id` (idempotent on re-run).
4. Recompute the per-user and per-repo rollups in §4.
5. Post the summary and the top action items to the enablement Slack channel, and open tickets for the environment fixes.

Store one row per session with at least:

```
session_id, user_id, team, repo, created_at, origin, devin_mode, playbook_id,
category, session_size, acus_consumed, num_user_messages, num_devin_messages,
status, status_detail, pr_url, pr_state, action_item_types[], issue_labels[]
```

Retention: raw prompts can be sensitive — store `suggested_prompt` diffs only for users who opt in to coaching, and keep aggregates otherwise.

---

## 4. The per-user scorecard

Computed over a rolling 30 days, per user, alongside the team median for context:

| Metric | Formula | Reads as |
| --- | --- | --- |
| Merged PRs | count(`pr_state == merged`) | Delivered value |
| Session→PR rate | sessions producing a PR ÷ sessions | Task selection and finishing |
| PR merge rate | merged PRs ÷ PRs opened | Output quality/trust |
| ACU per merged PR | Σ`acus_consumed` ÷ merged PRs | Efficiency |
| Median user messages | median(`num_user_messages`) | Prompt quality (high = course-correcting) |
| Small-session share | share of sessions with `session_size` ∈ {xs, s, m} | Task decomposition |
| Failure share | share with `status` ∈ {error} or `status_detail` ∈ {inactivity, error} | Environment/setup friction |
| Asset leverage | share of sessions with a `playbook_id` or a good `note_usage` hit | Whether org assets reach them |
| Surface mix | share of sessions with `origin` ∈ {slack, teams, linear, jira, cli} | Embedded in workflow vs. cold-start in the webapp |
| Cadence | active days per week with ≥1 session | Habit formation |

Two derived ratios do most of the diagnostic work:

- **Effort-to-output**: `ACU per merged PR` versus the team median.
- **Autonomy**: `num_user_messages` versus `acus_consumed`. High ACU with few messages means Devin flailed alone (environment or ambiguity). Many messages with low ACU means the user is steering constantly (prompting).

---

## 5. Segmentation

Assign each active user to exactly one segment, evaluated in order:

| Segment | Rule (relative to team) | Typical count |
| --- | --- | --- |
| **Dormant** | < 1 session per week | Largest group in most orgs |
| **Power** | Top-quartile merged PRs *and* below-median ACU per merged PR | 5–15% |
| **Environment-blocked** | Above-median failure share, or above-median ACU with below-median messages | Fix first: cheapest wins |
| **Prompt-limited** | Top-quartile median user messages, or bottom-quartile session→PR rate with normal ACU | Coachable |
| **Scope-mismatched** | Above-median L/XL share, or PRs opened but bottom-quartile merge rate | Needs task-selection help |
| **Solid** | Everyone else with ≥1 session/week | Maintain |

Also roll up **per repo** — `machine_setup` and `repo_config` action items concentrate in a handful of repos, and fixing those repos silently upgrades every user who touches them. This is usually the single highest-ROI output of the whole exercise.

---

## 6. Signal → root cause → intervention

| Signal | Likely root cause | Intervention | Owner |
| --- | --- | --- | --- |
| High `machine_setup` / `repo_config` action items; high failure share | Missing or stale blueprint; deps, services, or credentials absent | Fix the repo blueprint and rebuild the snapshot; add required secrets at org/repo scope | Platform/enablement |
| High ACU, few user messages, L/XL sizes | Ambiguous requirements → trial and error | Push Ask-Devin-first scoping; publish the prompt skeleton; split tasks | Champion + user |
| High user message count | Under-specified prompts | Coach with the session's own *Improved Prompt*; supply reference-file habits | Champion |
| Repeated `knowledge`-type action items across users | Tribal conventions not written down | Create/repair knowledge notes; pin repo-specific ones | Champion |
| PRs opened but low merge rate | Wrong tasks delegated, or no verification loop | Task menu (green/yellow/red); enable Devin Review + Auto-Fix; require explicit done-criteria | Team lead |
| Low asset leverage | Playbooks/notes exist but aren't discoverable | Promote macros (`!ticket_to_pr`), demo them live, wire them into ticket templates | Enablement |
| Weak prompts naming no files, on repos with no wiki | User does not know the codebase well enough to give context | Generate DeepWiki for the repo; teach Ask-Devin-first scoping | Enablement |
| Sessions only from the webapp | Not embedded in workflow | Connect Slack/Teams and the tracker; teach tagging Devin in-thread | Enablement |
| Dormant despite onboarding | No trusted first use case | 1:1 pairing on one real ticket from their own backlog | Champion |
| Bad `note_usage` entries | A knowledge note is misleading Devin | Rewrite or delete that note | Note owner |

---

## 7. Cadence and artifacts

| Cadence | Artifact | Audience |
| --- | --- | --- |
| Weekly | Top 5 failing repos by `machine_setup`/`repo_config` items; 3 worst sessions reviewed in the champion sync | Champions, platform |
| Monthly | Segment distribution and movement between segments; per-team scorecard | Team leads |
| Quarterly | Merged PRs per active user, ACU per merged PR trend, asset inventory audit (retire unused playbooks/notes) | Leadership |

Success for the program is **movement between segments** — dormant → solid, environment-blocked → solid — not raw usage growth. Track the count of users who moved, and which intervention preceded the move.

---

## 8. Implementation steps

1. Create a service user with analytics/session read access and store its key as an org secret.
2. Stand up the weekly scheduled session with the pull-and-summarize prompt (§3), writing to a CSV in a private repo or a warehouse table.
3. Backfill 90 days to establish baseline quartiles before setting any thresholds.
4. Publish the first per-repo environment fix list — do this before publishing anything user-facing, so the first visible output is the org fixing itself.
5. Name champions, start the weekly worst-session review, and only then share per-team scorecards.
6. Re-baseline quartiles quarterly.

**Starter prompt for the scheduled session:**

```
Pull all org sessions from the last 7 days via the session insights API.
For every session that is L/XL, ended in error/suspended, or produced no PR,
fetch its per-session insights so the analysis is generated.
Append the flattened rows to metrics/sessions.csv (idempotent on session_id).
Then output: (1) repos ranked by count of machine_setup/repo_config action items,
(2) users whose median user-message count is in the top quartile,
(3) the three sessions with the worst ACU-per-outcome, each with its improved prompt.
Do not include raw prompt text for users outside the coaching opt-in list.
```

---

## 9. Guardrails

- ACUs measure agent effort, not engineer productivity — never present ACU spend as an individual performance metric.
- Publish team-level scorecards openly; share individual scorecards only with that individual and their champion.
- Exclude experimentation and learning sessions (tag them) from efficiency metrics, so exploring the product is never penalised.
- Re-check thresholds after any major product or model change; yesterday's quartiles will not hold.
