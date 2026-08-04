# Issue tracker: Azure DevOps

Issues and PRDs for this repo live as Azure DevOps work items in the
**{project}** project. Use the `devops-utils azdo` CLI for all operations; the
same operations are exposed as `azdo_*` MCP tools by the `devops-utils-mcp`
server — prefer those when available.

## Defaults for this repo

| Setting | Value |
| --- | --- |
| Organization URL | {org_url} |
| Project | {project} |
| Parent Epic | {parent_epic} |
| Area Path | {area_path} |
| Default tags | {default_tags} |
| Done state | {done_state} |

Apply these defaults on every operation unless the user overrides them:

- **Creating**: parent new items under the parent Epic (or a Feature/Story
  beneath it), set the area path, and apply every default tag —
  `devops-utils azdo create --project {project} --type Task --title "..."{create_flags}`.
- **Querying**: scope searches with the same area path and tags so this repo's
  items surface first —
  `devops-utils azdo list --project {project}{query_flags}`.
  To walk the backlog under the parent Epic, filter by direct parent:
  `devops-utils azdo list --project {project} --parent {parent_epic_id}`.

If `devops-utils` is not on `PATH`, run it through `uvx` (assume `uv` is
installed): `uvx --from "devops-utils[azure]" devops-utils azdo …`. The
`[azure]` extra is required; every command below then works unchanged behind
that prefix.

## Configuration

Config comes only from environment variables (no machine credentials are read):
`AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_TOKEN`, and optional
`AZURE_DEVOPS_AUTH_SCHEME` (`bearer`/`pat`) and `AZURE_DEVOPS_API_VERSION`.
If a command fails with a missing-variable error, ask the user to fill in the
`.env` scaffold from `devops-utils setup env` — never hunt for credentials.

## Output contract

Every command prints its result as JSON on **stdout** and nothing else, so
`azdo get <id> --full | jq -r '.fields["System.Description"]'` is safe. Write
commands put their `About to write: {...}` preview, the
`(dry run — not applied)` marker, and the `Apply this change?` prompt on
**stderr**; `--dry-run` and a declined prompt leave stdout empty and exit 0.

Output is UTF-8 regardless of the calling shell's code page — no `chcp`,
`PYTHONUTF8`, or `PYTHONIOENCODING` preamble is needed for accented text.

## Conventions

- **Create an issue**: `devops-utils azdo create --project {project} --type Task --title "..." --description "<p>...</p>"`.
  The description is **HTML**, not markdown. Pick `--type` from the types the
  project actually uses (`Bug`, `Task`, `User Story`, `Feature`, …); if a type is
  rejected, check what existing items use via `azdo list`.
- **Read an issue**: `devops-utils azdo get <id>` returns a trimmed summary
  (id/type/title/state/assignee/tags/area/iteration). Add `--full` for the
  description, scheduling dates, and any `Custom.*` field — they come back as a
  `fields` map keyed by reference name, alongside `rev`. Add `--relations` for
  parent/child and PR/commit links; the two compose.
- **List issues**: `devops-utils azdo list --project {project} [--state Active] [--type Bug] [--assigned-to WHO] [--tag X] [--parent ID] [--area-path P] [--top N]`
  (`--state`/`--type`/`--tag` are repeatable; `--parent` matches direct
  children of a work-item id).
- **Find pending issues**: pending = the non-closed states, scoped by the
  defaults above —
  `devops-utils azdo list --project {project} --state New --state Active{query_flags}`.
- **Search issues**: `devops-utils azdo search --project {project} "TEXT"`
  (same filters as `list`, matched against title + description).
- **Comment on an issue**: `devops-utils azdo comment <id> "..."`.
- **Apply a label**: labels are work-item **tags** — `devops-utils azdo tag <id> <label> --mode add`.
- **Remove a label**: tags have no atomic remove; read the current tags with
  `azdo get <id>`, then rewrite the remaining set:
  `devops-utils azdo tag <id> <tag1> <tag2> --mode replace`.
- **Close**: `devops-utils azdo update <id> --state "{done_state}"` and leave a
  resolution comment. State names are process-template-specific; this project's
  done state is `{done_state}`.
- **Assign / claim**: `devops-utils azdo update <id> --assigned-to user@example.com`
  (email or display name; there is no `@me` shorthand — ask the user for their
  identity if unknown).
- **Blocking relationships**: use native dependency links —
  `devops-utils azdo link <id> --kind predecessor --value <blocker-id>` marks
  `<id>` as blocked by `<blocker-id>`; `--kind successor` is the reverse.
  Parent/child hierarchy: `--kind parent` / `--kind child`. Plain relation:
  `--kind work_item`.
- **Reference a PR / commit / branch**:
  `devops-utils azdo link <id> --kind pull_request --value <pr-id> --project {project} --repo <repo>`
  (likewise `--kind commit --value <sha>` and `--kind branch --value <name>`).
- **Reference a build**: `devops-utils azdo link <id> --kind build --value <build-id>`
  (no `--project`/`--repo` needed). Find the build id with
  `devops-utils azdo builds --project {project}`.
- **Comment on a PR**:
  `devops-utils azdo pr-comment <pr-id> "..." --project {project} --repo <repo>`.
  Commits cannot be commented on via the REST API — comment on the PR or the
  work item instead.
- **Attach a file**: `devops-utils azdo attach <id> ./path/to/file`.

## When a skill says "publish to the issue tracker"

Create a work item: `devops-utils azdo create --project {project} --type Task --title "..." --description "<p>...</p>"`.

## When a skill says "fetch the relevant ticket"

Run `devops-utils azdo get <id>`, or find it first with
`devops-utils azdo search --project {project} "..."`.
