# Wide Research Orchestration Playbook

When a user mentions “Wide Research” or references this file, load these instructions. You act as the primary Codex orchestrator coordinating reusable multi-agent workflows. Tasks may involve web research, code retrieval, API sampling, data cleaning, etc. Execute flexibly while staying safe and compliant. **Important: keep Codex’s default model and other low-level capability settings unless the user explicitly authorizes changes; explicitly request `model_reasoning_effort="low"` for this workflow.**

## Objectives
1. Parse the user’s high-level goals and derive the set of sub-goals that can be processed in parallel (e.g., link lists, dataset shards, module inventories).
2. Spawn a fresh Codex process for each sub-goal with the appropriate permissions (default to sandbox restrictions, only enable broader access when required).
3. Run child processes in parallel so they emit structured results (JSON/CSV/Markdown preferred); ensure failures return error objects with reasons.
4. Aggregate child outputs with scripts/programs only—do not rely on hand-written summaries—and produce a unified result file.
5. Perform a sanity check on the aggregation, apply minimal fixes if necessary, then report artefact paths and key findings back to the user.

## Detailed Procedure
0. **Pre-run planning & reconnaissance (mandatory)**
   - Always perform an up-front discovery pass yourself—do not delegate this phase. Clarify user intent, assess risks/resources, and identify the core dimensions that will anchor the Wide Research fan-out (e.g., topic clusters, stakeholder lists, geography slices, timeline buckets).
   - When public indices (tag pages, API lists, etc.) exist, cache them via minimal sandbox fetches and count entries. Otherwise, run light-touch desk research (news feeds, search, existing datasets) to surface representative items, capturing concrete evidence such as source URLs, timestamps, and key takeaways.
   - Before drafting any outline, demonstrate at least one actual sample gathered through this reconnaissance; purely experience-based speculation does not satisfy the scoping requirement.
   - If the current environment exposes the tavily search MCP service, you must invoke tavily MCP during this scoping pass to collect at least one directly relevant sample and record its citation; if tavily is unavailable, document the reason and name the fallback method you used instead.
   - Produce a provisional manifest (or outline) that captures the discovered dimension(s), the items collected for each, the supporting samples, and estimated scale. Highlight data gaps or uncertainties. If no real samples have been secured yet, continue the reconnaissance and do not advance to later steps.
   - Draft the executable plan (subtasks, scripts/tools, outputs, permissions, timeouts) using the newly surfaced structure, then report both the dimension inventory and plan to the user. Wait for an explicit “go/execute” before proceeding.

1. **Initialization**
   - Clarify goals, expected output formats, and evaluation criteria.
   - Create a semantic, unique run directory (e.g., `runs/<date>-<summary>-<suffix>`) that stores scripts, logs, child outputs, and aggregate results.
  - Keep the default model but explicitly set the reasoning effort with `-c model_reasoning_effort="low"`; only escalate if the user authorizes a higher tier.

2. **Identify sub-goals**
   - Extract or construct the subtask list via scripts/commands, assigning each item a unique identifier.
   - If the source provides fewer entries than expected, record the fact and continue with what is available.

3. **Generate the scheduler script**
   - Build a rerunnable driver script (e.g., `run_children.sh`) that:
     - Reads the subtask manifest (JSON/CSV) and dispatches each entry.
     - Invokes `codex exec` per subtask with recommended flags:
       - `--sandbox workspace-write`
       - add `-c sandbox_workspace_write.network_access=true` when network access is needed
       - avoid `--model` overrides unless the user requests them and pass `-c model_reasoning_effort="low"` by default; raise the effort only with explicit approval
       - write outputs under predictable paths such as `child_outputs/<id>.json`
     - size `timeout_ms` to the subtask: start with 5 minutes for lightweight work, allow up to 15 minutes for heavier runs, and wrap with `timeout` at the script level. If the first 5-minute window expires, reassess (split, tune, or extend) before retrying; hitting 15 minutes signals the prompt/flow needs debugging.
     - Implements parallelism via `xargs -P`, GNU Parallel, or background jobs + `wait`; default to 8 concurrent workers unless the task or infrastructure requires a different setting.
     - Capture exit codes while streaming logs into the run directory via `stdbuf -oL -eL codex exec … | tee logs/<id>.log` so operators can `tail -f` progress in real time.
   - The orchestrator should avoid downloading/parsing itself; delegate heavy lifting to child agents while you prepare prompts, templates, and environment.

4. **Design child prompts**
   - Dynamically generate prompt templates that include:
     - description of the subtask, inputs, and boundaries
     - explicit permission constraints (only allowed domains/folders, permitted tools)
     - an explicit ban on using the plan tool or waiting for extra user interaction—children must complete the job in one pass
     - a consistent output schema, e.g.:
       ```json
       { "id": "...", "status": "ok", "summary": "...", "details": [...], "sources": [...], "notes": "..." }
       ```
     - failure responses shaped as `{ "id": "...", "status": "error", "reason": "..." }`
   - Write templates to files (e.g., `child_prompt_template.md`) so the workflow is auditable and reusable.

5. **Parallel execution & monitoring**
   - Run the scheduler.
   - Track for each child: start/end time, duration, status.
   - For failures/timeouts decide whether to mark, retry, or document the issue for the final report; once the 15-minute cap is reached, treat it as a prompt/workflow defect that must be logged. Encourage users to `tail -f logs/<id>.log` during long runs.

6. **Programmatic aggregation**
   - Use scripts (e.g., `aggregate.py`) to read everything in `child_outputs/`, merge/sort/deduplicate, and compute metrics.
   - Emit a master result file (e.g., `runs/<...>/aggregate.json` or `final_report.csv`).
   - Validate during aggregation (field completeness, valid JSON, unique IDs).

7. **Final review & minor fixes**
   - Sanity-check aggregated results.
   - Apply minimal programmatic fixes (spelling, field order, missing metadata) when needed; do not rewrite child content wholesale.
   - Optionally create a README or metadata file to document extra context.

8. **Deliverables**
   - Summarize key metrics (# subtasks, success/failure counts, retries) and main issues.
   - Share final artefact paths, supporting scripts, and recommended next steps.
   - Highlight the run directory so the user can inspect or rerun.

## Output Expectations
- The orchestrator’s standard output should log status per stage, list child output files, provide aggregation paths, and note errors.
- The final response must cite the resulting artefact(s) and describe discoveries or future actions.

## Notes & Safety
- Keep runs idempotent: each execution uses a fresh run directory to avoid overwriting data.
- All structured outputs must be valid UTF-8 with no trailing commas.
- Escalate permissions only when justified; avoid `--dangerously-bypass-approvals-and-sandbox`.
- Handle cleanup carefully so logs and outputs remain traceable.
- Provide downgraded structured outputs for failures: child prompts must attempt fetches twice and, if both attempts fail, emit `status: "error"` with a concrete `error` message so aggregation never lacks an entry.
- The sample “three-link web page” is illustrative—adapt subtask detection and output format to your task.
- **Cache first**: download raw materials into the run directory (`raw/`) before processing and reuse cached files to minimize duplicate fetches.
- **Read fully before summarizing**: do not truncate by fixed length (e.g., first 500 chars). Write scripts to parse the full content, extract key sentences, or compute highlights.
- **Keep temporary assets isolated**: store intermediates (logs, parsed text, caches, scratch data) under `tmp/`, `raw/`, `cache/` and clean up only when appropriate.
- **Child autonomy**: prompts must instruct children to execute end-to-end independently (no waiting for human approval, no plan calls) and supply concrete snippets (e.g., Python templates, `curl` commands) so they can act immediately.
- **Search provider preference**: before launching search-heavy subtasks, inspect the active MCP servers (e.g., via `codex mcp list`). If `tavily-remote` is available, route all search requests through Tavily; fall back to Codex’s built-in search only when Tavily is absent.
- **Tavily request settings**: default to `max_results=6` (raise to 10 if coverage is lacking), set `search_depth="advanced"`, and set `include_answer="advanced"` so responses include Tavily’s synthesized summary. Add `include_images` / `include_image_descriptions` when visuals help, and avoid `include_raw_content` to prevent oversized payloads; note that `include_answer` must be the string `"advanced"`, not a boolean.
- **Image retrieval with Tavily**: Tavily’s MCP server can return images. Unless the user explicitly wants text-only results, enable Tavily’s image search and surface relevant visuals alongside textual findings.

## Best Practices
- **Parameterize extraction logic**: do not assume identical DOM structures. Provide configurable selectors or fallbacks so the same script works across sites with minor tweaks.
- **Validate before scaling**: dry-run 1–2 subtasks sequentially to confirm parsing/aggregation, then fan out in parallel to avoid mass failures.
- **Structured outputs first**: always include `status`/`reason` fields so aggregation can gracefully handle missing or erroneous data.
- **Balance caching & logging**: store raw HTML, cleaned text, and execution logs separately (`raw/`, `tmp/`, `logs/`) for traceability and to reduce redundant downloads.
- **Validate JSON outputs**: after each child run, confirm the resulting JSON parses; if it fails, delete the bad file and rerun that child before proceeding.
- **Avoid duplicate fetches**: when retrying, skip any child whose `child_outputs/<id>.json` already exists and passes validation to save quota and respect rate limits.
- **Manual review entry points**: allow lightweight edits of JSON fields or add validation scripts so humans can quickly intervene when long-tail pages misbehave.
- **Coverage checks**: after batch generation, run a small script to flag missing entries, empty fields, or label counts before shipping the report.
- **Scope & permissions isolation**: specify allowed domains/directories/tools per child prompt to avoid accidental overreach and keep the workflow safe on any site.
- **Final polish**: before the handoff, the orchestrator must review the summary/aggregate for language requirements (e.g., produce Chinese when requested), verify citations/data, add concise analysis (trends/risks), and keep all key facts/figures intact so the deliverable reads like a finished insight report.
- **Presentation style**: cite sources inline right after each bullet using Markdown links (e.g., `[source](https://example.com)`), rather than dumping URLs at the end, to make fact-checking immediate.

## Example
- `scripts/wide_research_example.sh` demonstrates the end-to-end flow: caching an index, generating child prompts, running `codex exec` in parallel, and validating JSON outputs. The script first fetches `https://yage.ai/tag/deepseek.html` to measure scope, then delegates download/parse/summary work to child agents and checks their outputs at the end.
