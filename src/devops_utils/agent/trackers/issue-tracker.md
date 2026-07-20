# Issue tracker: Azure DevOps

Issues and PRDs for this repo live as Azure DevOps work items in the
**{project}** project. Use the `devops-utils azdo` CLI for all operations; the
same operations are exposed as `azdo_*` MCP tools by the `devops-utils-mcp`
server — prefer those when available.

## Configuration

Config comes only from environment variables (no machine credentials are read):
`AZURE_DEVOPS_ORG_URL`, `AZURE_DEVOPS_TOKEN`, and optional
`AZURE_DEVOPS_AUTH_SCHEME` (`bearer`/`pat`) and `AZURE_DEVOPS_API_VERSION`.
If a command fails with a missing-variable error, ask the user to fill in the
`.env` scaffold from `devops-utils setup env` — never hunt for credentials.

## Conventions

- **Create an issue**: `devops-utils azdo create --project {project} --type Task --title "..." --description "<p>...</p>"`.
  The description is **HTML**, not markdown. Pick `--type` from the types the
  project actually uses (`Bug`, `Task`, `User Story`, `Feature`, …); if a type is
  rejected, check what existing items use via `azdo list`.
- **Read an issue**: `devops-utils azdo get <id>`.
- **List issues**: `devops-utils azdo list --project {project} [--state Active] [--type Bug] [--assigned-to WHO] [--top N]`
  (`--state`/`--type` are repeatable).
- **Search issues**: `devops-utils azdo search --project {project} "TEXT"`.
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
- **Attach a file**: `devops-utils azdo attach <id> ./path/to/file`.

## When a skill says "publish to the issue tracker"

Create a work item: `devops-utils azdo create --project {project} --type Task --title "..." --description "<p>...</p>"`.

## When a skill says "fetch the relevant ticket"

Run `devops-utils azdo get <id>`, or find it first with
`devops-utils azdo search --project {project} "..."`.
