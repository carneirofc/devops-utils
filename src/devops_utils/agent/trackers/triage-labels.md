# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to the work-item **tag** strings used in this project's Azure DevOps
tracker (apply them with `devops-utils azdo tag <id> <tag> --mode add`).

| Label in mattpocock/skills | Tag in our tracker | Meaning                                  |
| -------------------------- | ------------------ | ---------------------------------------- |
| `needs-triage`             | `needs-triage`     | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`       | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`  | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`  | Requires human implementation            |
| `wontfix`                  | `wontfix`          | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the
corresponding tag string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.
