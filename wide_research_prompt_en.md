# Wide Research Orchestration Playbook

When a user mentions “Wide Research” or references this file, load these instructions. You act as the primary Codex orchestrator coordinating reusable multi-agent workflows. Tasks may involve web research, code retrieval, API sampling, data cleaning, etc. Execute flexibly while staying safe and compliant.

## Objectives
1. Parse the user’s high-level goals and derive the set of sub-goals that can be processed in parallel (e.g., link lists, dataset shards, module inventories).
2. Spawn a fresh Codex process for each sub-goal with the appropriate permissions (default to sandbox restrictions, only enable broader access when required).
3. Run child processes in parallel so they emit structured results (JSON/CSV/Markdown preferred); ensure failures return error objects with reasons.
4. Aggregate child outputs with scripts/programs only—do not rely on hand-written summaries—and produce a unified result file.
5. Perform a sanity check on the aggregation, apply minimal fixes if necessary, then report artefact paths and key findings back to the user.

## Detailed Procedure
0. **Pre-run planning (mandatory)**
   - Understand the user intent and context; estimate scope, risks, and required resources.
   - If the task depends on a public index (tag page, API list, etc.), first cache it via a minimal sandbox fetch, count the entries, and share scale information with the user for confirmation.
   - Draft an executable plan (subtask breakdown, tools/scripts, outputs, permissions, timeouts) and present it in the user’s language.
   - Ask explicitly whether to proceed. Do not continue without an affirmative “go/execute” response.

1. **Initialization**
   - Clarify goals, expected output formats, and evaluation criteria.
   - Create a semantic, unique run directory (e.g., `runs/<date>-<summary>-<suffix>`) that stores scripts, logs, child outputs, and aggregate results.
  - Select the model and reasoning effort; default to the stable tier unless the task warrants `model_reasoning_effort = "high"`.

2. **Identify sub-goals**
   - Extract or construct the subtask list via scripts/commands, assigning each item a unique identifier.
   - If the source provides fewer entries than expected, record the fact and continue with what is available.

3. **Generate the scheduler script**
   - Build a rerunnable driver script (e.g., `run_children.sh`) that:
     - Reads the subtask manifest (JSON/CSV) and dispatches each entry.
     - Invokes `codex exec` per subtask with recommended flags:
       - `--sandbox workspace-write`
       - add `-c sandbox_workspace_write.network_access=true` when network access is needed
       - provide `--model` and `-c model_reasoning_effort="high"` as required
       - write outputs under predictable paths such as `child_outputs/<id>.json`
     - size `timeout_ms` to the subtask: start with 5 minutes for lightweight work, allow up to 15 minutes for heavier runs, and wrap with `timeout` at the script level. If the first 5-minute window expires, reassess (split, tune, or extend) before retrying; hitting 15 minutes signals the prompt/flow needs debugging.
     - Implements parallelism via `xargs -P`, GNU Parallel, or background jobs + `wait`.
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

## Best Practices
- **Parameterize extraction logic**: do not assume identical DOM structures. Provide configurable selectors or fallbacks so the same script works across sites with minor tweaks.
- **Validate before scaling**: dry-run 1–2 subtasks sequentially to confirm parsing/aggregation, then fan out in parallel to avoid mass failures.
- **Structured outputs first**: always include `status`/`reason` fields so aggregation can gracefully handle missing or erroneous data.
- **Balance caching & logging**: store raw HTML, cleaned text, and execution logs separately (`raw/`, `tmp/`, `logs/`) for traceability and to reduce redundant downloads.
- **Manual review entry points**: allow lightweight edits of JSON fields or add validation scripts so humans can quickly intervene when long-tail pages misbehave.
- **Coverage checks**: after batch generation, run a small script to flag missing entries, empty fields, or label counts before shipping the report.
- **Scope & permissions isolation**: specify allowed domains/directories/tools per child prompt to avoid accidental overreach and keep the workflow safe on any site.

## Example
- `scripts/wide_research_example.sh` demonstrates the end-to-end flow: caching an index, generating child prompts, running `codex exec` in parallel, and validating JSON outputs. The script first fetches `https://yage.ai/tag/deepseek.html` to measure scope, then delegates download/parse/summary work to child agents and checks their outputs at the end.
