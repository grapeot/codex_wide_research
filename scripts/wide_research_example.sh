#!/usr/bin/env bash
# Example wide-research orchestrator that delegates work to Codex agents.
# It scaffolds prompt templates and calls codex exec so that child agents
# handle downloading, parsing, and summarising blog posts listed on an index
# page. The script is designed to be rerunnable and keeps all artefacts under
# a timestamped run directory.

set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found in PATH; install or load it before running." >&2
  exit 127
fi

INDEX_URL="${1:-https://yage.ai/tag/deepseek.html}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="runs/${STAMP}-wide-research"

RAW_DIR="${RUN_DIR}/raw"
PROMPT_DIR="${RUN_DIR}/child_prompts"
OUTPUT_DIR="${RUN_DIR}/child_outputs"
LOG_DIR="${RUN_DIR}/logs"

mkdir -p "${RAW_DIR}" "${PROMPT_DIR}" "${OUTPUT_DIR}" "${LOG_DIR}"

MODEL="${MODEL:-}"
codex_opts=("--sandbox" "workspace-write" "--cd" "${RUN_DIR}" "-c" "sandbox_workspace_write.network_access=true")
if [[ -n "${MODEL}" ]]; then
  codex_opts+=("--model" "${MODEL}")
fi

# -----------------------------------------------------------------------------
# Prompt template: download & parse the index page
# -----------------------------------------------------------------------------
INDEX_PROMPT_TEMPLATE="${PROMPT_DIR}/download_index.template.md"
cat <<'EOF' > "${INDEX_PROMPT_TEMPLATE}"
# Role
You are Codex agent "Indexer" running with workspace-write sandbox access.

# Objective
Given the inputs below, download the index HTML if not already cached, extract
all blog post entries, and emit a JSON manifest describing them.

# Inputs
- `INDEX_URL`: absolute URL of the tag/index page.
- `INDEX_HTML_PATH`: local target path for the cached HTML.
- `OUTPUT_JSON_PATH`: where to write the manifest JSON.

# Constraints
- Use `curl -sSL "$INDEX_URL" -o "$INDEX_HTML_PATH.tmp"` followed by an atomic
  rename to avoid torn writes. If the final HTML file already exists, reuse it.
- Do not scrape other domains; stick to the received URL and relative links on
  that page.
- Produce UTF-8 JSON with the structure:
  ```json
  {
    "status": "ok",
    "fetched_at": "<ISO8601>",
    "source_url": "...",
    "posts": [
      {
        "id": "post-###",
        "title": "...",
        "url": "...",
        "summary_hint": "short excerpt if available"
      }
    ]
  }
  ```
- IDs must be zero-padded indices in the order discovered (e.g., post-001).
- Resolve relative links against `INDEX_URL`. Skip duplicates.
- Write the manifest with `json.dump(..., ensure_ascii=False, indent=2)`.
- On error, emit `{ "status": "error", "reason": "...", "stage": "..." }`.
- Execute autonomously; do not pause for external confirmation or emit plan-tool
  messages that require approval.

# Deliverable
Save the JSON to `OUTPUT_JSON_PATH` and print a one-line success message.

# Runtime Parameters
- INDEX_URL: ${INDEX_URL}
- INDEX_HTML_PATH: ${INDEX_HTML_PATH}
- OUTPUT_JSON_PATH: ${OUTPUT_JSON_PATH}
EOF

# -----------------------------------------------------------------------------
# Prompt template: download & summarise individual posts
# -----------------------------------------------------------------------------
POST_PROMPT_TEMPLATE="${PROMPT_DIR}/summarise_post.template.md"
cat <<'EOF' > "${POST_PROMPT_TEMPLATE}"
# Role
You are Codex agent "Summariser" with workspace-write sandbox access.

# Objective
For the specified blog post, ensure the HTML is cached locally, extract the
content, and summarise it into structured JSON.

# Inputs
- `POST_ID`: unique identifier (e.g., post-001).
- `POST_TITLE`: title from the index manifest.
- `POST_URL`: absolute URL to download.
- `POST_HTML_PATH`: cache location for the raw HTML.
- `POST_TEXT_PATH`: optional plaintext extraction path.
- `OUTPUT_JSON_PATH`: path for the summary JSON.

# Tasks
1. If `POST_HTML_PATH` is missing, download with `curl -sSL`.
2. Parse the article content (prefer `.entry-content` or `<article>` tags).
3. Derive a concise 3–5 sentence summary aimed at technically savvy readers.
4. List 3–5 bullet highlights focusing on concrete insights.
5. Record processing notes (language, caveats, missing sections, etc.).

# Output Format
Write UTF-8 JSON shaped as:
```json
{
  "id": "...",
  "status": "ok",
  "title": "...",
  "url": "...",
  "summary": "...",
  "highlights": ["..."],
  "notes": "...",
  "error": ""
}
```
- Use empty string/array when data is unavailable.
- If anything fails, set `status` to `"error"` and populate `error`.

# Additional Guidance
- Store intermediate plaintext in `POST_TEXT_PATH` for reproducibility.
- Avoid long verbatim quotes; paraphrase instead.
- Ensure the final JSON is valid (use Python `json` module).
- Execute autonomously without waiting for approvals; skip plan-tool usage that
  would halt progress.

# Output Instructions
在撰写好 summary / highlights / notes 后，请编辑并运行以下 Python 片段，将占位符替换成你的实际内容，再执行：
```
python - <<'PY'
import json
from pathlib import Path

data = {
    "id": "${POST_ID}",
    "status": "ok",
    "title": "${POST_TITLE}",
    "url": "${POST_URL}",
    "summary": """<<<SUMMARY>>>""",
    "highlights": [
        "<<<H1>>>",
        "<<<H2>>>",
        "<<<H3>>>"
    ],
    "notes": "<<<NOTES>>>",
    "error": ""
}
output_path = Path("${OUTPUT_JSON_PATH}")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
print(f"Wrote {output_path}")
PY
```
执行后用 `cat ${OUTPUT_JSON_PATH}` 自查一次，确认 JSON 写入成功。

# Runtime Parameters
- POST_ID: ${POST_ID}
- POST_TITLE: ${POST_TITLE}
- POST_URL: ${POST_URL}
- POST_HTML_PATH: ${POST_HTML_PATH}
- POST_TEXT_PATH: ${POST_TEXT_PATH}
- OUTPUT_JSON_PATH: ${OUTPUT_JSON_PATH}
EOF

# -----------------------------------------------------------------------------
# Step 1: delegate index fetching / parsing to Codex
# -----------------------------------------------------------------------------
INDEX_HTML_REL="raw/index.html"
INDEX_JSON_REL="child_outputs/index_manifest.json"
INDEX_HTML_PATH="${RUN_DIR}/${INDEX_HTML_REL}"
INDEX_JSON_PATH="${RUN_DIR}/${INDEX_JSON_REL}"

INDEX_PROMPT="${PROMPT_DIR}/download_index.prompt.md"
INDEX_URL="${INDEX_URL}" INDEX_HTML_PATH="${INDEX_HTML_REL}" OUTPUT_JSON_PATH="${INDEX_JSON_REL}" \
  envsubst < "${INDEX_PROMPT_TEMPLATE}" > "${INDEX_PROMPT}"

cat "${INDEX_PROMPT}" | codex exec \
  "${codex_opts[@]}" \
  > "${LOG_DIR}/indexer.log" 2>&1

if [[ ! -s "${INDEX_JSON_PATH}" ]]; then
  echo "Indexer failed: ${INDEX_JSON_PATH} is missing or empty." >&2
  exit 1
fi

# Abort if indexer reported error
if jq -e '.status != "ok"' "${INDEX_JSON_PATH}" >/dev/null; then
  echo "Indexer reported error:"
  cat "${INDEX_JSON_PATH}"
  exit 1
fi
# -----------------------------------------------------------------------------
# Step 2: fan out per-post summarisation
# -----------------------------------------------------------------------------
jq -r '
  select(.status == "ok") |
  .posts[] |
  @base64
' "${INDEX_JSON_PATH}" | while read -r encoded; do
  _jq() { echo "${encoded}" | base64 --decode | jq -r "${1}"; }

  POST_ID="$(_jq ".id")"
  POST_TITLE="$(_jq ".title")"
  POST_URL="$(_jq ".url")"

  POST_HTML_REL="raw/${POST_ID}.html"
  POST_TEXT_REL="raw/${POST_ID}.txt"
  POST_JSON_REL="child_outputs/${POST_ID}.json"
  POST_HTML_PATH="${RUN_DIR}/${POST_HTML_REL}"
  POST_TEXT_PATH="${RUN_DIR}/${POST_TEXT_REL}"
  POST_JSON_PATH="${RUN_DIR}/${POST_JSON_REL}"
  POST_LOG_PATH="${LOG_DIR}/${POST_ID}.log"

  POST_PROMPT="${PROMPT_DIR}/${POST_ID}.prompt.md"
  POST_ID="${POST_ID}" \
  POST_TITLE="${POST_TITLE}" \
  POST_URL="${POST_URL}" \
  POST_HTML_PATH="${POST_HTML_REL}" \
  POST_TEXT_PATH="${POST_TEXT_REL}" \
  OUTPUT_JSON_PATH="${POST_JSON_REL}" \
    envsubst < "${POST_PROMPT_TEMPLATE}" > "${POST_PROMPT}"

  cat "${POST_PROMPT}" | codex exec \
    "${codex_opts[@]}" \
    > "${POST_LOG_PATH}" 2>&1 &
done

wait

all_ok=true
while read -r post_id; do
  post_json="${RUN_DIR}/child_outputs/${post_id}.json"
  if [[ ! -s "${post_json}" ]]; then
    echo "Missing summary for ${post_id} at ${post_json}" >&2
    all_ok=false
    continue
  fi
  if jq -e '.status != "ok"' "${post_json}" >/dev/null; then
    echo "Child ${post_id} reported error:" >&2
    cat "${post_json}"
    all_ok=false
  fi
done < <(jq -r '.posts[].id' "${INDEX_JSON_PATH}")

if [[ "${all_ok}" != "true" ]]; then
  exit 1
fi

echo "Child outputs stored under ${OUTPUT_DIR}"
